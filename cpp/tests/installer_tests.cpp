#include "installer.hpp"

#include <chrono>
#include <iostream>

namespace {

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

template<class F>
void rejects(F action) {
    try { action(); }
    catch (const std::exception&) { return; }
    throw std::runtime_error("Expected operation to fail");
}

xcom::Bytes bytes(const std::string& value) {
    return {value.begin(), value.end()};
}

struct Fixture {
    xcom::Path root = std::filesystem::temp_directory_path()
        / ("xcom-installer-tests-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    xcom::Path exe = root / "game/XEW/Binaries/Win32/XComEW.exe";
    xcom::Path package = root / "game/XEW/XComGame/CookedPCConsole/XComGame.upk";
    xcom::Path other = package.parent_path() / "XComStrategyGame.upk";
    xcom::Path tools = root / "tools/Binaries";
    xcom::Bytes clean{'M', 'Z'};
    std::string script = "UPK_FILE = XComGame.upk\nUPK_FILE = XComStrategyGame.upk\n";
    xcom::Installer installer{root, {}};
    unsigned patches = 0;
    bool unchanged = false;
    bool omit_undo = false;

    Fixture() {
        std::filesystem::create_directories(exe.parent_path());
        std::filesystem::create_directories(package.parent_path());
        std::filesystem::create_directories(root / "mods");
        std::filesystem::create_directories(tools);
        for (const auto& patch : xcom::patches()) {
            clean.insert(clean.end(), patch.original.begin(), patch.original.end());
            clean.push_back(0);
        }
        xcom::write_file_atomic(exe, clean);
        reset_packages();
        xcom::write_file_atomic(installer.patch_script(), bytes(script));
        xcom::write_file_atomic(tools / "DecompressLZO.exe", {});
        xcom::write_file_atomic(tools / "PatchUPK.exe", {});

        installer.run_tool = [&](const std::vector<xcom::Path>& args, const xcom::Path& cwd) {
            if (args.front().filename() == "DecompressLZO.exe") {
                if (args[1] == other) throw std::runtime_error("Package is already decompressed!");
                xcom::write_file_atomic(args[2], xcom::read_file(args[1]));
                return;
            }
            ++patches;
            const bool restoring = args[1].filename().u8string().find(".uninstall.txt") != std::string::npos;
            const auto targets = xcom::package_locations(root / "game", args[1]);
            for (const auto& target : targets) {
                require(std::filesystem::is_regular_file(cwd / target.filename()), "Missing staged package");
                if (!unchanged) xcom::write_file_atomic(cwd / target.filename(),
                    bytes(std::string(restoring ? "restored " : "changed ") + target.filename().u8string()));
            }
            if (!omit_undo) {
                auto undo = args[1];
                undo += ".uninstall.txt";
                xcom::write_file_atomic(undo, xcom::read_file(args[1]));
            }
        };
    }

    ~Fixture() {
        std::error_code error;
        std::filesystem::remove_all(root, error);
    }

    void reset_packages() {
        xcom::write_file_atomic(package, bytes("original"));
        xcom::write_file_atomic(other, bytes("other original"));
        xcom::write_file_atomic(xcom::Path(package.wstring() + L".uncompressed_size"), bytes("size"));
    }

    void execute(xcom::Action action) {
        installer.execute(action, root / "game", root / "tools", [](const std::string&) {});
    }
};

void install_restore() {
    Fixture f;
    f.execute(xcom::Action::install);
    require(f.patches == 1, "PatchUPK must run once for all targets");
    require(xcom::read_file(f.exe) == xcom::install(f.clean), "EXE not installed");
    require(std::filesystem::exists(f.installer.uninstall_script()), "Missing undo script");
    require(!std::filesystem::exists(xcom::Path(f.package.wstring() + L".uncompressed_size")), "Sidecar retained");
    f.execute(xcom::Action::install);
    require(f.patches == 1, "Repeated installation staged UPKs");

    auto edited = xcom::read_file(f.exe);
    edited.push_back(42);
    xcom::write_file_atomic(f.exe, edited);
    // Restore must use the uninstall script's subset, rather than the bundled script.
    xcom::write_file_atomic(f.installer.uninstall_script(), bytes("UPK_FILE=XComGame.upk\n"));
    const auto other = xcom::read_file(f.other);
    f.execute(xcom::Action::restore);
    auto expected = f.clean;
    expected.push_back(42);
    require(xcom::read_file(f.exe) == expected, "Unrelated EXE edits lost");
    require(xcom::read_file(f.other) == other, "Restore touched a package absent from undo script");
    require(!std::filesystem::exists(f.installer.uninstall_script()), "Undo script retained");
    require(xcom::read_file(xcom::Path(f.exe.wstring() + L".bak")) == f.clean, "First EXE backup replaced");
}

void rollback() {
    Fixture f;
    f.installer.write = [&](const xcom::Path& path, const xcom::Bytes& data) {
        xcom::write_file_atomic(path, data);
        if (path == f.other && data != bytes("other original"))
            throw std::runtime_error("Simulated failure after replacing second package");
    };
    rejects([&] { f.execute(xcom::Action::install); });
    require(xcom::read_file(f.exe) == f.clean, "EXE rollback failed");
    require(xcom::read_file(f.package) == bytes("original"), "First package rollback failed");
    require(xcom::read_file(f.other) == bytes("other original"), "Second package rollback failed");
    require(xcom::read_file(xcom::Path(f.package.wstring() + L".uncompressed_size")) == bytes("size"), "Sidecar rollback failed");
    require(!std::filesystem::exists(f.installer.uninstall_script()), "Failed install left undo script");

    f.installer.write = xcom::write_file_atomic;
    f.execute(xcom::Action::install);
    const auto patched = xcom::read_file(f.exe);
    f.installer.write = [&](const xcom::Path& path, const xcom::Bytes& data) {
        if (path == f.other) throw std::runtime_error("Restore write failure");
        xcom::write_file_atomic(path, data);
    };
    rejects([&] { f.execute(xcom::Action::restore); });
    require(xcom::read_file(f.exe) == patched, "Restore EXE rollback failed");
    require(std::filesystem::exists(f.installer.uninstall_script()), "Failed restore removed undo script");
}

void validation() {
    Fixture f;
    f.unchanged = true;
    rejects([&] { f.execute(xcom::Action::install); });
    require(xcom::read_file(f.exe) == f.clean, "Unchanged staging wrote EXE");
    f.unchanged = false;
    f.omit_undo = true;
    rejects([&] { f.execute(xcom::Action::install); });
    require(xcom::read_file(f.package) == bytes("original"), "Missing undo wrote package");

    xcom::write_file_atomic(f.installer.patch_script(), bytes("UPK_FILE=../XComGame.upk\n"));
    rejects([&] { f.execute(xcom::Action::install); });
    xcom::write_file_atomic(f.installer.patch_script(), bytes("UPK_FILE=Missing.upk\n"));
    rejects([&] { f.execute(xcom::Action::install); });
    xcom::write_file_atomic(f.installer.patch_script(), bytes("\xef\xbb\xbfupk_file=xcomgame.UPK // comment\nUPK_FILE=XComGame.upk\n"));
    require(xcom::package_locations(f.root / "game", f.installer.patch_script()).size() == 1, "Target parsing/deduplication failed");

    std::filesystem::remove_all(f.root / "tools");
    f.execute(xcom::Action::install_exe);
    f.execute(xcom::Action::status);
    f.execute(xcom::Action::restore);
    require(xcom::read_file(f.exe) == f.clean, "EXE-only restore failed without tools");
    xcom::save_game_directory(f.root, f.root / "game");
    require(xcom::load_game_directory(f.root) == std::filesystem::absolute(f.root / "game"), "Settings roundtrip failed");
}

}

int main() {
    try {
        install_restore();
        rollback();
        validation();
        std::cout << "All installer checks passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
