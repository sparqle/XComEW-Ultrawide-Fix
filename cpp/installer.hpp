#pragma once

#include "exe_patcher.hpp"

#include <functional>
#include <optional>

namespace xcom
{

using Path = std::filesystem::path;
using Log = std::function<void(const std::string&)>;
using ToolRunner = std::function<void(const std::vector<Path>&, const Path&)>;
using FileWriter = std::function<void(const Path&, const Bytes&)>;

enum class Action
{
    install,
    restore,
    status,
    install_exe,
    phone_home
};

Path executable_location(const Path& base);
Path find_game_directory(const Path& preferred = {});
Path load_game_directory(const Path& app_folder);
void save_game_directory(const Path& app_folder, const Path& base);
Path binaries_folder(const Path& folder);
std::vector<Path> package_locations(const Path& base, const Path& script);

// Dependencies can be replaced by tests without running tools or touching a real game.
struct Installer
{
    Path app_folder;
    ToolRunner run_tool;
    FileWriter write = write_file_atomic;

    Path patch_script() const;
    Path uninstall_script() const;
    bool needs_tools(Action action) const;
    void execute(Action action, const Path& base, const Path& tools, const Log& log) const;
};

} // namespace xcom
