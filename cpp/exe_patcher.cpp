#include "exe_patcher.hpp"

#include <algorithm>
#include <fstream>
#include <iterator>
#include <stdexcept>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#else
#include <unistd.h>
#endif

namespace xcom {
#include "signatures.inc"

namespace {

std::vector<std::size_t> find_all(const Bytes& data, const Bytes& needle) {
    std::vector<std::size_t> hits;
    auto pos = data.begin();

    while ((pos = std::search(pos, data.end(), needle.begin(), needle.end())) != data.end()) {
        hits.push_back(static_cast<std::size_t>(pos - data.begin()));
        ++pos;
    }

    return hits;
}

void replace(Bytes& data, std::size_t offset, const Bytes& replacement) {
    std::copy(replacement.begin(), replacement.end(), data.begin() + offset);
}

Bytes utf16(const std::string& value) {
    Bytes result;

    // The known host names are ASCII, so each UTF-16LE code unit has a zero high byte.
    for (unsigned char ch : value) {
        result.push_back(ch);
        result.push_back(0);
    }

    return result;
}

void atomic_write(const std::filesystem::path& path, const Bytes& data) {
    // Keep the temporary file on the same filesystem so replacement is atomic.
#ifdef _WIN32
    wchar_t temp_name[MAX_PATH];
    auto parent = std::filesystem::absolute(path).parent_path();
    if (!GetTempFileNameW(parent.c_str(), L"xcm", 0, temp_name))
        throw std::runtime_error("Cannot create temporary file beside executable");
    const std::filesystem::path temp(temp_name);

    try {
        HANDLE file = CreateFileW(temp.c_str(), GENERIC_WRITE, 0, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file == INVALID_HANDLE_VALUE) throw std::runtime_error("Cannot open temporary file");

        bool ok = true;
        std::size_t offset = 0;
        while (offset < data.size()) {
            DWORD written = 0;
            DWORD count = static_cast<DWORD>(std::min<std::size_t>(data.size() - offset, 1024 * 1024));
            if (!WriteFile(file, data.data() + offset, count, &written, nullptr) || written == 0) {
                ok = false;
                break;
            }

            offset += written;
        }

        if (!FlushFileBuffers(file)) ok = false;
        CloseHandle(file);
        if (!ok) throw std::runtime_error("Cannot flush temporary executable");

        const bool replaced = std::filesystem::exists(path)
            ? ReplaceFileW(path.c_str(), temp.c_str(), nullptr, 0, nullptr, nullptr) != 0
            : MoveFileExW(temp.c_str(), path.c_str(), MOVEFILE_WRITE_THROUGH) != 0;
        if (!replaced)
            throw std::runtime_error("Cannot replace executable; close the game and check permissions");
    } catch (...) {
        std::filesystem::remove(temp);
        throw;
    }
#else
    auto pattern = path.string() + ".XXXXXX";
    std::vector<char> name(pattern.begin(), pattern.end());
    name.push_back(0);

    int fd = mkstemp(name.data());
    if (fd < 0) throw std::runtime_error("Cannot create temporary file");
    const std::filesystem::path temp(name.data());

    try {
        std::size_t offset = 0;
        while (offset < data.size()) {
            auto written = ::write(fd, data.data() + offset, data.size() - offset);
            if (written <= 0) throw std::runtime_error("Cannot write temporary file");
            offset += static_cast<std::size_t>(written);
        }

        if (fsync(fd)) throw std::runtime_error("Cannot flush temporary file");
        close(fd);
        fd = -1;

        if (std::filesystem::exists(path))
            std::filesystem::permissions(temp, std::filesystem::status(path).permissions());
        std::filesystem::rename(temp, path);
    } catch (...) {
        if (fd >= 0) close(fd);
        std::filesystem::remove(temp);
        throw;
    }
#endif
}

}

void write_file_atomic(const std::filesystem::path& path, const Bytes& data) {
    atomic_write(path, data);
}

State inspect(const Bytes& data) {
    bool clean = true, patched = true;

    // Every signature must occur exactly once in the same state; mixed states are unsupported.
    for (const auto& p : patches()) {
        auto a = find_all(data, p.original), b = find_all(data, p.patched);
        clean = clean && a.size() == 1 && b.empty();
        patched = patched && a.empty() && b.size() == 1;
    }

    return clean ? State::clean : patched ? State::patched : State::unsupported;
}

Bytes install(const Bytes& data) {
    if (inspect(data) == State::patched) return data;
    if (inspect(data) != State::clean) throw std::invalid_argument("Expected a completely clean executable; no changes made");

    Bytes result = data;
    for (const auto& p : patches()) {
        replace(result, find_all(data, p.original).front(), p.patched);
    }

    if (inspect(result) != State::patched) throw std::runtime_error("Patch verification failed");
    return result;
}

Bytes restore(const Bytes& data) {
    Bytes result = data;

    // Accept mixed clean/patched blocks, but require an unambiguous match for each block.
    for (const auto& p : patches()) {
        auto clean = find_all(data, p.original), changed = find_all(data, p.patched);
        if (clean.size() + changed.size() != 1)
            throw std::invalid_argument("Unrecognized or ambiguous " + p.name + " block; no changes made");

        if (!changed.empty()) replace(result, changed.front(), p.original);
    }

    if (inspect(result) != State::clean) throw std::runtime_error("Restore verification failed");
    return result;
}

Bytes disable_phone_home(const Bytes& data) {
    Bytes result = data;
    bool found = false;
    const auto replacement = utf16("xcm.invalid");

    // All three names have the same encoded length, preserving executable offsets.
    for (const auto* host : {"firaxis.com", "yiraxis.com", "xcm.invalid"}) {
        auto needle = utf16(host);

        for (auto offset : find_all(data, needle)) {
            auto end = offset + needle.size();

            // Require UTF-16 alignment and a host boundary to avoid replacing a substring.
            if (offset % 2 || end + 1 >= data.size() || data[end + 1] != 0) continue;
            auto ch = data[end];
            if (ch != 0 && ch != '/' && ch != ':' && ch != '?' && ch != '#') continue;

            found = true;
            replace(result, offset, replacement);
        }
    }

    if (!found) throw std::invalid_argument("No recognized phone home address; no changes made");
    return result;
}

Bytes read_file(const std::filesystem::path& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw std::runtime_error("Cannot open executable");

    Bytes data{std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()};
    if (in.bad()) throw std::runtime_error("Cannot read executable");
    return data;
}

bool apply_file(const std::filesystem::path& path, Operation operation, bool dry_run) {
    const auto original = read_file(path);
    const auto result = operation == Operation::install ? install(original)
        : operation == Operation::restore ? restore(original)
        : disable_phone_home(original);

    if (result == original || dry_run) return result != original;

    auto backup = path;
    backup += ".bak";

    // copy_file with no overwrite preserves the first snapshot.
    std::error_code error;
    if (!std::filesystem::copy_file(path, backup, std::filesystem::copy_options::none, error)
        && error && error != std::errc::file_exists)
        throw std::filesystem::filesystem_error("Cannot create backup", path, backup, error);

    try {
        atomic_write(path, result);
        if (read_file(path) != result) throw std::runtime_error("Post-write verification failed");
    } catch (...) {
        // Restore the bytes from this operation, never an older .bak snapshot.
        if (read_file(path) != original) atomic_write(path, original);
        throw;
    }

    return true;
}

}
