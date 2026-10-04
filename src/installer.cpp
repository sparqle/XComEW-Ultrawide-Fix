#include "installer.hpp"

#include <algorithm>
#include <cctype>
#include <chrono>
#include <exception>
#include <fstream>
#include <map>
#include <regex>
#include <sstream>

namespace xcom
{
namespace
{

constexpr const char* config = "XComEW-Ultrawide-Fix.cfg";

std::string lower(std::string value)
{
    std::transform(value.begin(), value.end(), value.begin(),
                   [](unsigned char ch)
                   {
                       return static_cast<char>(std::tolower(ch));
                   });
    return value;
}

std::string trim(const std::string& value)
{
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos)
        return {};
    return value.substr(first, value.find_last_not_of(" \t\r\n") - first + 1);
}

Path sidecar(const Path& package)
{
    auto path = package;
    path += ".uncompressed_size";
    return path;
}

std::optional<Bytes> snapshot(const Path& path)
{
    return std::filesystem::exists(path) ? std::optional<Bytes>(read_file(path)) : std::nullopt;
}

void backup(const Path& path)
{
    auto destination = path;
    destination += ".bak";
    std::error_code error;
    std::filesystem::copy_file(path, destination, std::filesystem::copy_options::none, error);
    if (error && error != std::errc::file_exists)
        throw std::filesystem::filesystem_error("Cannot create backup", path, destination, error);
}

struct Workspace
{
    Path path;

    Workspace()
    {
        const auto stamp = std::chrono::steady_clock::now().time_since_epoch().count();
        for (unsigned i = 0; i < 100; ++i)
        {
            path = std::filesystem::temp_directory_path() /
                   ("xcomew-ultrawide-" + std::to_string(stamp) + "-" + std::to_string(i));
            if (std::filesystem::create_directory(path))
                return;
        }
        throw std::runtime_error("Cannot create staging directory");
    }

    ~Workspace()
    {
        std::error_code error;
        std::filesystem::remove_all(path, error);
    }
};

struct Staged
{
    std::map<Path, Bytes> packages;
    std::optional<Bytes> undo;
};

Staged stage(const Installer& installer, const std::vector<Path>& packages, const Path& tools, const Path& script,
             bool uninstall, const Log& log)
{
    if (!installer.run_tool)
        throw std::runtime_error("UPK tool runner unavailable");
    const auto binaries = binaries_folder(tools);
    Workspace workspace;
    const auto staged_script = workspace.path / script.filename();
    std::filesystem::copy_file(script, staged_script);
    std::map<Path, Bytes> before;

    // All packages share one workspace because PatchUPK resolves cross-package references.
    for (const auto& package : packages)
    {
        const auto unpacked = workspace.path / package.filename();
        try
        {
            installer.run_tool({binaries / "DecompressLZO.exe", package, unpacked}, workspace.path);
        }
        catch (const std::runtime_error& error)
        {
            if (std::string(error.what()).find("Package is already decompressed!") == std::string::npos)
                throw;
            std::filesystem::copy_file(package, unpacked, std::filesystem::copy_options::overwrite_existing);
        }

        before[package] = read_file(unpacked);
        if (before[package].empty())
            throw std::runtime_error("DecompressLZO produced an empty package");
    }

    installer.run_tool({binaries / "PatchUPK.exe", staged_script, workspace.path}, workspace.path);
    Staged result;
    for (const auto& package : packages)
    {
        auto bytes = read_file(workspace.path / package.filename());
        if (bytes.empty())
            throw std::runtime_error("PatchUPK produced an empty package: " + package.filename().u8string());
        if (bytes == before.at(package))
            log("PatchUPK did not change " + package.filename().u8string() + "; continuing.");
        result.packages.emplace(package, std::move(bytes));
    }

    if (!uninstall)
    {
        auto undo = staged_script;
        undo += ".uninstall.txt";
        result.undo = read_file(undo);
        if (result.undo->empty())
            throw std::runtime_error("PatchUPK generated an empty uninstall script");
    }
    return result;
}

} // namespace

Path executable_location(const Path& base)
{
    const auto exe = std::filesystem::absolute(base) / "XEW/Binaries/Win32/XComEW.exe";
    if (!std::filesystem::is_regular_file(exe))
        throw std::invalid_argument("Select the XCom-Enemy-Unknown directory; expected " + exe.u8string());
    return exe;
}

Path find_game_directory(const Path& preferred)
{
    std::error_code error;
    if (!preferred.empty() && std::filesystem::is_directory(preferred, error))
        return std::filesystem::absolute(preferred);

    for (const auto* root :
         {"Program Files/Steam", "Program Files (x86)/Steam", "Steam", "SteamLibrary", "Games/Steam"})
    {
        for (const auto* drive : {"C:/", "D:/"})
        {
            const auto candidate = Path(drive) / root / "SteamApps/common/XCom-Enemy-Unknown";
            if (std::filesystem::is_directory(candidate, error))
                return candidate;
        }
    }
    return {};
}

Path load_game_directory(const Path& app_folder)
{
    try
    {
        const auto bytes = read_file(app_folder / config);
        std::string value(bytes.begin(), bytes.end());
        if (value.compare(0, 3, "\xef\xbb\xbf") == 0)
            value.erase(0, 3);
        return find_game_directory(std::filesystem::u8path(trim(value)));
    }
    catch (const std::exception&)
    {
        return find_game_directory();
    }
}

void save_game_directory(const Path& app_folder, const Path& base)
{
    if (base.empty() || !std::filesystem::is_directory(base))
        return;
    const auto value = std::filesystem::absolute(base).u8string() + "\n";
    write_file_atomic(app_folder / config, Bytes(value.begin(), value.end()));
}

Path binaries_folder(const Path& folder)
{
    for (const auto& candidate : {folder, folder / "Binaries"})
    {
        if (std::filesystem::is_regular_file(candidate / "DecompressLZO.exe") &&
            std::filesystem::is_regular_file(candidate / "PatchUPK.exe"))
            return std::filesystem::absolute(candidate);
    }
    throw std::invalid_argument("Select a PatcherGUI or UPKUtils folder containing DecompressLZO.exe and PatchUPK.exe");
}

std::vector<Path> package_locations(const Path& base, const Path& script)
{
    const auto bytes = read_file(script);
    std::string contents(bytes.begin(), bytes.end());
    if (contents.compare(0, 3, "\xef\xbb\xbf") == 0)
        contents.erase(0, 3);
    std::istringstream lines(contents);
    const std::regex target(R"(^\s*UPK_FILE\s*=\s*(.*?)(?:\s*//.*)?$)", std::regex::icase);
    const auto directory = std::filesystem::absolute(base) / "XEW/XComGame/CookedPCConsole";
    std::vector<Path> result;

    for (std::string line; std::getline(lines, line);)
    {
        // PatchUPK writes CRLF. ECMAScript's dot does not match the leftover CR.
        if (!line.empty() && line.back() == '\r')
            line.pop_back();

        std::smatch match;
        if (!std::regex_match(line, match, target))
            continue;
        const auto name = trim(match[1].str());
        if (name.empty() || name.find_first_of("/\\:") != std::string::npos ||
            lower(std::filesystem::u8path(name).extension().u8string()) != ".upk")
            throw std::invalid_argument("Invalid UPK_FILE target: " + name);

        std::vector<Path> matches;
        for (const auto& entry : std::filesystem::directory_iterator(directory))
        {
            if (entry.is_regular_file() && lower(entry.path().filename().u8string()) == lower(name))
                matches.push_back(entry.path());
        }
        if (matches.size() != 1)
            throw std::invalid_argument("Missing or ambiguous UPK target: " + name);
        if (std::find(result.begin(), result.end(), matches.front()) == result.end())
            result.push_back(matches.front());
    }

    if (result.empty())
        throw std::invalid_argument("No UPK_FILE targets in " + script.u8string());
    return result;
}

Path Installer::patch_script() const
{
    return app_folder / "mods/Fix-ultrawide-UI.txt";
}

Path Installer::uninstall_script() const
{
    auto path = patch_script();
    path += ".uninstall.txt";
    return path;
}

bool Installer::needs_tools(Action action) const
{
    return (action == Action::install && !std::filesystem::exists(uninstall_script())) ||
           (action == Action::restore && std::filesystem::exists(uninstall_script()));
}

void Installer::execute(Action action, const Path& base, const Path& tools, const Log& log) const
{
    const auto exe = executable_location(base);
    const auto original = read_file(exe);
    const auto script = uninstall_script();

    if (action == Action::status)
    {
        const auto state = inspect(original);
        log(state == State::clean     ? "EXE: CLEAN / UNPATCHED"
            : state == State::patched ? "EXE: FULLY PATCHED"
                                      : "EXE: UNSUPPORTED / PARTIALLY PATCHED");
        log(std::filesystem::is_regular_file(script) ? "UI UPK patches: installed (uninstall script present)"
                                                     : "UI UPK patches: not installed (no uninstall script)");
        return;
    }

    const bool restoring = action == Action::restore;
    const auto result = restoring                      ? restore(original)
                        : action == Action::phone_home ? disable_phone_home(original)
                                                       : install(original);
    Staged staged;
    if (needs_tools(action))
    {
        const auto source = restoring ? script : patch_script();
        if (read_file(source).empty())
            throw std::invalid_argument("Empty UPK patch script");
        const auto targets = package_locations(base, source);
        for (const auto& package : targets)
            log("Detected UPK: " + package.filename().u8string());
        staged = stage(*this, targets, tools.empty() ? app_folder / "third_party" : tools, source, restoring, log);
    }
    else if (action == Action::install)
    {
        if (!std::filesystem::is_regular_file(script))
            throw std::invalid_argument("Invalid uninstall script path");
        log("UI UPK patches: already installed (uninstall script present)");
    }

    struct Original
    {
        Bytes bytes;
        std::optional<Bytes> size;
    };
    std::map<Path, Original> originals;
    for (const auto& item : staged.packages)
        originals.emplace(item.first, Original{read_file(item.first), snapshot(sidecar(item.first))});

    if (result != original)
        backup(exe);
    bool written_exe = false;
    bool created_script = false;
    std::vector<Path> written_packages;

    try
    {
        // Persist the undo script before the first game write, so a successful install is reversible.
        if (staged.undo)
        {
            created_script = true;
            write(script, *staged.undo);
        }

        if (result != original)
        {
            written_exe = true;
            write(exe, result);
            if (read_file(exe) != result)
                throw std::runtime_error("EXE verification failed");
        }

        for (const auto& item : staged.packages)
        {
            // Record attempts before writing: a writer can fail after replacing the file.
            written_packages.push_back(item.first);
            write(item.first, item.second);
            std::filesystem::remove(sidecar(item.first));
            if (read_file(item.first) != item.second)
                throw std::runtime_error("UPK verification failed");
        }

        if (restoring && !staged.packages.empty() && !std::filesystem::remove(script))
            throw std::runtime_error("Cannot remove uninstall script");
    }
    catch (...)
    {
        const auto failure = std::current_exception();
        std::string rollback_errors;
        const auto attempt = [&](const auto& task)
        {
            try
            {
                task();
            }
            catch (const std::exception& error)
            {
                rollback_errors += std::string(error.what()) + "\n";
            }
        };

        // Attempt every rollback even if one file cannot be restored.
        if (written_exe)
            attempt(
                [&]
                {
                    write(exe, original);
                });
        for (const auto& package : written_packages)
        {
            attempt(
                [&]
                {
                    write(package, originals.at(package).bytes);
                });
            attempt(
                [&]
                {
                    const auto& size = originals.at(package).size;
                    if (size)
                        write(sidecar(package), *size);
                    else
                        std::filesystem::remove(sidecar(package));
                });
        }
        // Retain recovery instructions if any game files failed to roll back.
        if (created_script && rollback_errors.empty())
            attempt(
                [&]
                {
                    std::filesystem::remove(script);
                });
        if (!rollback_errors.empty())
        {
            try
            {
                std::rethrow_exception(failure);
            }
            catch (const std::exception& error)
            {
                throw std::runtime_error(std::string(error.what()) + "\nRollback incomplete:\n" + rollback_errors);
            }
        }
        std::rethrow_exception(failure);
    }

    log(result == original && staged.packages.empty() ? "Already in requested state."
        : restoring                                   ? "Restore completed; unrelated EXE modifications retained."
                                                      : "Operation completed and verified.");
}

} // namespace xcom
