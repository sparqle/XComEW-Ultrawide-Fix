#pragma once

#include "installer.hpp"

namespace xcom
{

Path application_folder();
std::wstring from_utf8(const std::string& value);
void run_windows_tool(const std::vector<Path>& args, const Path& cwd);

} // namespace xcom
