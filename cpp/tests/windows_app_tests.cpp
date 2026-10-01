#include "windows_support.hpp"

#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

#include <chrono>
#include <iostream>

namespace
{

void require(bool condition, const char* message)
{
    if (!condition)
        throw std::runtime_error(message);
}

struct Workspace
{
    xcom::Path root =
        std::filesystem::temp_directory_path() /
        (L"xcom native tests \u00e9 " + std::to_wstring(std::chrono::steady_clock::now().time_since_epoch().count()));

    Workspace()
    {
        std::filesystem::create_directory(root);
    }
    ~Workspace()
    {
        std::error_code error;
        std::filesystem::remove_all(root, error);
    }
};

struct WindowSearch
{
    DWORD process;
    HWND window = nullptr;
};

BOOL CALLBACK find_window(HWND window, LPARAM context)
{
    auto& search = *reinterpret_cast<WindowSearch*>(context);
    DWORD process = 0;
    GetWindowThreadProcessId(window, &process);
    wchar_t name[128]{};
    GetClassNameW(window, name, 128);
    if (process == search.process && std::wstring(name) == L"XComEWUltrawideFix")
    {
        search.window = window;
        return FALSE;
    }
    return TRUE;
}

void gui_smoke(const xcom::Path& app, const xcom::Path& cwd)
{
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESHOWWINDOW;
    startup.wShowWindow = SW_HIDE;
    PROCESS_INFORMATION process{};
    std::wstring command = L"\"" + app.wstring() + L"\"";
    require(CreateProcessW(app.c_str(), command.data(), nullptr, nullptr, FALSE, 0, nullptr, cwd.c_str(), &startup,
                           &process) != 0,
            "GUI did not start");

    try
    {
        require(WaitForInputIdle(process.hProcess, 10000) == 0, "GUI did not become ready");
        WindowSearch search{process.dwProcessId};
        EnumWindows(find_window, reinterpret_cast<LPARAM>(&search));
        require(search.window != nullptr, "Native application window missing");
        require(GetDlgItem(search.window, 100) != nullptr, "Game folder entry missing");
        require(GetDlgItem(search.window, 101) != nullptr, "Tools folder entry missing");
        for (int id = 104; id <= 107; ++id)
            require(GetDlgItem(search.window, id) != nullptr, "Operation button missing");
        PostMessageW(search.window, WM_CLOSE, 0, 0);
        require(WaitForSingleObject(process.hProcess, 10000) == WAIT_OBJECT_0, "GUI did not close cleanly");
        DWORD code = 1;
        GetExitCodeProcess(process.hProcess, &code);
        require(code == 0, "GUI exited with an error");
    }
    catch (...)
    {
        TerminateProcess(process.hProcess, 1);
        WaitForSingleObject(process.hProcess, INFINITE);
        CloseHandle(process.hThread);
        CloseHandle(process.hProcess);
        throw;
    }

    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
}

} // namespace

int wmain(int argc, wchar_t** argv)
{
    // Run this binary as a fake external tool to exercise real Windows process handling.
    if (argc > 1 && std::wstring(argv[1]) == L"--child")
    {
        if (argc != 5 || std::wstring(argv[2]) != L"folder with spaces\\" ||
            std::wstring(argv[3]) != L"embedded\"quote\u00e9")
            return 9;
        if (std::wstring(argv[4]) == L"fail")
        {
            std::cout << std::string(12000, 'x') << "\nPackage is already decompressed!\n";
            return 5;
        }
        return 0;
    }

    try
    {
        Workspace workspace;
        const auto folder = xcom::application_folder();
        for (const auto& entry : std::filesystem::directory_iterator(folder))
        {
            if (entry.path().extension() == ".dll" || entry.path().filename() == "windows_app_tests.exe" ||
                entry.path().filename() == "XComEW-Ultrawide-Fix.exe")
                std::filesystem::copy_file(entry.path(), workspace.root / entry.path().filename());
        }
        const auto helper = workspace.root / "windows_app_tests.exe";
        const std::vector<xcom::Path> args{helper, L"--child", L"folder with spaces\\", L"embedded\"quote\u00e9",
                                           L"success"};
        xcom::run_windows_tool(args, workspace.root);
        auto failing = args;
        failing.back() = L"fail";
        bool rejected = false;
        try
        {
            xcom::run_windows_tool(failing, workspace.root);
        }
        catch (const std::runtime_error& error)
        {
            const std::string message = error.what();
            rejected = message.find("failed (5)") != std::string::npos &&
                       message.find("Package is already decompressed!") != std::string::npos;
        }
        require(rejected, "Tool failure/output capture incorrect");
        gui_smoke(workspace.root / "XComEW-Ultrawide-Fix.exe", workspace.root);
        std::cout << "Windows process and GUI startup checks passed\n";
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
