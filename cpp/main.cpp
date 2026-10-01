#include "exe_patcher.hpp"

#include <iostream>

int run(int argc, const std::filesystem::path* args) {
    try {
        xcom::Operation operation = xcom::Operation::install;
        bool status = false, dry_run = false, selected = false;
        std::filesystem::path path;

        for (int i = 1; i < argc; ++i) {
            const auto arg = args[i].string();

            if (arg == "--help") {
                std::cout << "Usage: xcomew-patcher <XComEW.exe or containing directory>\n"
                    "  [--status | --restore | --disable-phone-home] [--dry-run]\n"
                    "Default: install EXE patches only. UPK files are not modified.\n";
                return 0;
            }

            if (arg == "--dry-run") {
                dry_run = true;
                continue;
            }

            if (arg == "--status" || arg == "--restore" || arg == "--disable-phone-home") {
                if (selected) throw std::invalid_argument("Choose only one operation");

                // Status also occupies the operation slot, despite being read-only.
                selected = true;
                status = arg == "--status";
                operation = arg == "--restore" ? xcom::Operation::restore
                    : arg == "--disable-phone-home" ? xcom::Operation::disable_phone_home
                    : xcom::Operation::install;
            } else if (arg.rfind("--", 0) == 0 || !path.empty()) {
                throw std::invalid_argument("Unknown argument or multiple executable paths");
            } else {
                path = args[i];
            }
        }

        if (path.empty()) throw std::invalid_argument("Pass the executable path; use --help for usage");
        if (std::filesystem::is_directory(path)) path /= "XComEW.exe";

        if (status) {
            auto state = xcom::inspect(xcom::read_file(path));
            std::cout << (state == xcom::State::clean ? "CLEAN / UNPATCHED\n"
                : state == xcom::State::patched ? "FULLY PATCHED\n"
                : "UNSUPPORTED / PARTIALLY PATCHED\n");
            return state == xcom::State::unsupported ? 2 : 0;
        }

        bool changed = xcom::apply_file(path, operation, dry_run);
        std::cout << (dry_run ? "Dry run verified; no files changed.\n"
            : changed ? "Operation completed and verified.\n"
            : "Already in requested state; no files changed.\n");
        return 0;
    } catch (const std::invalid_argument& error) {
        std::cerr << "Error: " << error.what() << '\n';
        return 2;
    } catch (const std::exception& error) {
        std::cerr << "Error: " << error.what() << '\n';
        return 1;
    }
}

// Use wide arguments on Windows to preserve Unicode executable paths.
#ifdef _WIN32
int wmain(int argc, wchar_t** argv) {
#else
int main(int argc, char** argv) {
#endif
    std::vector<std::filesystem::path> args(argv, argv + argc);
    return run(argc, args.data());
}
