#include "exe_patcher.hpp"

#include <algorithm>
#include <chrono>
#include <fstream>
#include <iostream>
#include <stdexcept>

void require(bool condition, const char* message)
{
    if (!condition)
        throw std::runtime_error(message);
}

template <class F> void rejects(F action)
{
    try
    {
        action();
    }
    catch (const std::invalid_argument&)
    {
        return;
    }

    throw std::runtime_error("Unsafe input accepted");
}

xcom::Bytes text(const std::string& value)
{
    xcom::Bytes out;

    // Match the executable's null-terminated UTF-16LE host strings.
    for (auto ch : value)
    {
        out.push_back(ch);
        out.push_back(0);
    }

    out.insert(out.end(), {0, 0});
    return out;
}

void write(const std::filesystem::path& path, const xcom::Bytes& data)
{
    std::ofstream out(path, std::ios::binary);
    out.write(reinterpret_cast<const char*>(data.data()), static_cast<std::streamsize>(data.size()));
    if (!out)
        throw std::runtime_error("Test fixture write failed");
}

int main()
{
    std::filesystem::path temp;

    try
    {
        xcom::Bytes clean{'M', 'Z'}, patched{'M', 'Z'};

        for (const auto& p : xcom::patches())
        {
            require(p.original.size() == p.patched.size(), "Patch length mismatch");
            clean.insert(clean.end(), p.original.begin(), p.original.end());
            clean.push_back(0);
            patched.insert(patched.end(), p.patched.begin(), p.patched.end());
            patched.push_back(0);
        }

        auto other = text("xcm.invalid");
        clean.insert(clean.end(), other.begin(), other.end());
        patched.insert(patched.end(), other.begin(), other.end());

        require(xcom::install(clean) == patched, "Installation failed");
        require(xcom::install(patched) == patched, "Install not idempotent");
        require(xcom::restore(patched) == clean, "Restore changed unrelated bytes");
        require(xcom::restore(clean) == clean, "Restore not idempotent");

        auto partial = clean;
        const auto& cursor = xcom::patches()[0];
        // The first patch follows the two-byte MZ header in this synthetic fixture.
        std::copy(cursor.patched.begin(), cursor.patched.end(), partial.begin() + 2);
        rejects(
            [&]
            {
                xcom::install(partial);
            });
        require(xcom::restore(partial) == clean, "Partial restore failed");

        auto duplicate = patched;
        duplicate.insert(duplicate.end(), cursor.patched.begin(), cursor.patched.end());
        rejects(
            [&]
            {
                xcom::install(duplicate);
            });
        rejects(
            [&]
            {
                xcom::restore(duplicate);
            });
        rejects(
            [&]
            {
                xcom::restore(xcom::Bytes{});
            });

        for (const auto* host : {"firaxis.com", "yiraxis.com", "xcm.invalid"})
        {
            require(xcom::disable_phone_home(text(host)) == text("xcm.invalid"), "Phone home replacement failed");
        }

        rejects(
            [&]
            {
                xcom::disable_phone_home(text("firaxis.company"));
            });
        auto unaligned = text("firaxis.com");
        unaligned.insert(unaligned.begin(), 0);
        rejects(
            [&]
            {
                xcom::disable_phone_home(unaligned);
            });

        temp = std::filesystem::temp_directory_path() /
               ("xcom-cpp-test-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
        std::filesystem::create_directory(temp);
        auto path = temp / "XComEW.exe";
        auto backup = temp / "XComEW.exe.bak";
        write(path, clean);

        xcom::apply_file(path, xcom::Operation::install, true);
        require(xcom::read_file(path) == clean && !std::filesystem::exists(backup), "Dry run wrote files");

        xcom::apply_file(path, xcom::Operation::install, false);
        require(xcom::read_file(path) == patched && xcom::read_file(backup) == clean, "Install or backup failed");

        // An older backup must survive restore; restoration uses signatures instead.
        write(backup, {'o', 'l', 'd'});
        xcom::apply_file(path, xcom::Operation::restore, false);
        require(xcom::read_file(path) == clean, "File restore failed");
        require(xcom::read_file(backup) == xcom::Bytes({'o', 'l', 'd'}), "First backup overwritten");

        write(path, duplicate);
        rejects(
            [&]
            {
                xcom::apply_file(path, xcom::Operation::install, false);
            });
        require(xcom::read_file(path) == duplicate, "Rejected install wrote executable");

        std::filesystem::remove_all(temp);
        std::cout << "All patcher checks passed\n";
        return 0;
    }
    catch (const std::exception& error)
    {
        if (!temp.empty())
            std::filesystem::remove_all(temp);
        std::cerr << error.what() << '\n';
        return 1;
    }
}
