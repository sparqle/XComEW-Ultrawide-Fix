#include "windows_support.hpp"

#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <commctrl.h>
#include <shlobj.h>

#include <memory>
#include <thread>

namespace
{

constexpr UINT log_message = WM_APP + 1;
constexpr UINT done_message = WM_APP + 2;
enum Control
{
    game = 100,
    tools,
    browse_game,
    browse_tools,
    install,
    restore,
    status,
    download,
    install_exe,
    phone_home,
    about,
    game_label,
    tools_label,
    log_label
};

struct Window
{
    HWND handle = nullptr;
    HWND game_edit = nullptr;
    HWND tools_edit = nullptr;
    HWND output = nullptr;
    HFONT font = nullptr;
    HWND status_bar = nullptr;
    UINT dpi = 96;
    std::vector<HWND> controls;
    std::thread worker;
    bool busy = false;
    xcom::Installer installer{xcom::application_folder(), xcom::run_windows_tool};

    ~Window()
    {
        if (worker.joinable())
            worker.join();
        if (font)
            DeleteObject(font);
    }

    HWND control(const wchar_t* type, const wchar_t* label, DWORD style, int x, int y, int width, int height,
                 int id = 0)
    {
        const auto child =
            CreateWindowExW(type == std::wstring(L"EDIT") ? WS_EX_CLIENTEDGE : 0, type, label,
                            WS_CHILD | WS_VISIBLE | style, x, y, width, height, handle,
                            reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)), GetModuleHandleW(nullptr), nullptr);
        SendMessageW(child, WM_SETFONT, reinterpret_cast<WPARAM>(font), TRUE);
        return child;
    }

    int pixels(int value) const
    {
        return MulDiv(value, dpi, 96);
    }

    void layout()
    {
        if (!status_bar)
            return;

        SendMessageW(status_bar, WM_SIZE, 0, 0);
        RECT client{}, status_rect{};
        GetClientRect(handle, &client);
        GetWindowRect(status_bar, &status_rect);
        const int width = MulDiv(client.right, 96, dpi);
        const int height = MulDiv(client.bottom - (status_rect.bottom - status_rect.top), 96, dpi);
        const auto place = [&](HWND child, int x, int y, int w, int h)
        {
            SetWindowPos(child, nullptr, pixels(x), pixels(y), pixels(w), pixels(h), SWP_NOZORDER | SWP_NOACTIVATE);
        };

        // Keep the path fields and log flexible; the browse/action column stays fixed.
        for (int row = 0; row < 2; ++row)
        {
            const int y = 12 + row * 34;
            place(GetDlgItem(handle, row == 0 ? game_label : tools_label), 12, y + 4, 106, 20);
            place(row == 0 ? game_edit : tools_edit, 122, y, width - 226, 24);
            place(GetDlgItem(handle, row == 0 ? browse_game : browse_tools), width - 96, y, 84, 24);
        }

        place(GetDlgItem(handle, log_label), 12, 84, 200, 20);
        place(output, 12, 106, width - 120, height - 118);
        place(GetDlgItem(handle, install), width - 96, 106, 84, 28);
        place(GetDlgItem(handle, restore), width - 96, 144, 84, 28);
        place(GetDlgItem(handle, status), width - 96, 182, 84, 28);
    }

    void activity(const wchar_t* message)
    {
        SendMessageW(status_bar, SB_SETTEXTW, 0, reinterpret_cast<LPARAM>(message));
    }

    void enable_controls(bool enabled)
    {
        for (const auto child : controls)
            EnableWindow(child, enabled);
        for (const auto id : {install_exe, phone_home, download})
            EnableMenuItem(GetMenu(handle), id, MF_BYCOMMAND | (enabled ? MF_ENABLED : MF_GRAYED));
        DrawMenuBar(handle);
    }

    static std::wstring text(HWND edit)
    {
        std::wstring value(GetWindowTextLengthW(edit) + 1, L'\0');
        GetWindowTextW(edit, value.data(), static_cast<int>(value.size()));
        value.resize(value.size() - 1);
        const auto first = value.find_first_not_of(L" \t\r\n");
        return first == std::wstring::npos ? L"" : value.substr(first, value.find_last_not_of(L" \t\r\n") - first + 1);
    }

    void log(const std::wstring& message)
    {
        const auto line = message + L"\r\n";
        SendMessageW(output, EM_SETSEL, static_cast<WPARAM>(-1), static_cast<LPARAM>(-1));
        SendMessageW(output, EM_REPLACESEL, FALSE, reinterpret_cast<LPARAM>(line.c_str()));
        SendMessageW(output, EM_SCROLLCARET, 0, 0);
    }

    void save()
    {
        try
        {
            xcom::save_game_directory(installer.app_folder, xcom::Path(text(game_edit)));
        }
        catch (const std::exception& error)
        {
            log(L"Could not save folder: " + xcom::from_utf8(error.what()));
        }
    }

    void browse(HWND edit)
    {
        IFileOpenDialog* dialog = nullptr;
        if (FAILED(CoCreateInstance(CLSID_FileOpenDialog, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&dialog))))
            return;
        DWORD options = 0;
        dialog->GetOptions(&options);
        dialog->SetOptions(options | FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM);
        dialog->SetTitle(edit == game_edit ? L"Select XCom-Enemy-Unknown folder"
                                           : L"Select PatcherGUI or UPKUtils folder");
        if (SUCCEEDED(dialog->Show(handle)))
        {
            IShellItem* item = nullptr;
            if (SUCCEEDED(dialog->GetResult(&item)))
            {
                PWSTR path = nullptr;
                if (SUCCEEDED(item->GetDisplayName(SIGDN_FILESYSPATH, &path)))
                {
                    SetWindowTextW(edit, path);
                    CoTaskMemFree(path);
                }
                item->Release();
            }
        }
        dialog->Release();
        if (edit == game_edit)
            save();
    }

    void start(xcom::Action action)
    {
        if (busy)
            return;
        try
        {
            const auto base = xcom::find_game_directory(xcom::Path(text(game_edit)));
            if (base.empty())
                throw std::invalid_argument("Could not locate XCOM. Select your XCom-Enemy-Unknown folder.");
            SetWindowTextW(game_edit, base.c_str());
            xcom::executable_location(base);
            save();
            xcom::Path binaries;
            if (installer.needs_tools(action))
            {
                const auto selected = text(tools_edit);
                binaries = xcom::binaries_folder(selected.empty() ? installer.app_folder / "third_party"
                                                                  : xcom::Path(selected));
            }

            if (action == xcom::Action::phone_home)
            {
                const auto bytes = xcom::read_file(xcom::executable_location(base));
                if (xcom::disable_phone_home(bytes) == bytes)
                {
                    log(L"Phone home already disabled: xcm.invalid");
                    return;
                }
                if (MessageBoxW(handle,
                                L"Replace the phone home address with xcm.invalid?\n\n"
                                L"PatcherGUI's yiraxis.com is now registered. The .invalid domain is reserved. Close "
                                L"the game first.",
                                L"Disable Phone Home", MB_YESNO | MB_ICONQUESTION | MB_DEFBUTTON2) != IDYES)
                    return;
            }

            if (worker.joinable())
                worker.join();
            busy = true;
            enable_controls(false);
            activity(action == xcom::Action::restore      ? L"Restoring..."
                     : action == xcom::Action::status     ? L"Checking status..."
                     : action == xcom::Action::phone_home ? L"Disabling phone home..."
                                                          : L"Installing...");
            log(L"Working...");
            try
            {
                worker = std::thread(
                    [this, action, base, binaries]
                    {
                        std::wstring failure;
                        const auto post = [&](const std::string& line)
                        {
                            auto value = std::make_unique<std::wstring>(xcom::from_utf8(line));
                            if (PostMessageW(handle, log_message, 0, reinterpret_cast<LPARAM>(value.get())))
                                value.release();
                        };
                        try
                        {
                            installer.execute(action, base, binaries, post);
                            post("Done.");
                        }
                        catch (const std::exception& error)
                        {
                            failure = xcom::from_utf8(error.what());
                            post(std::string("Error: ") + error.what());
                        }
                        auto value = std::make_unique<std::wstring>(failure);
                        if (PostMessageW(handle, done_message, 0, reinterpret_cast<LPARAM>(value.get())))
                            value.release();
                    });
            }
            catch (...)
            {
                busy = false;
                enable_controls(true);
                activity(L"Operation failed");
                throw;
            }
        }
        catch (const std::exception& error)
        {
            MessageBoxW(handle, xcom::from_utf8(error.what()).c_str(), L"XCOM EW Ultrawide Fix", MB_OK | MB_ICONERROR);
        }
    }

    void create()
    {
        const auto screen = GetDC(handle);
        dpi = GetDeviceCaps(screen, LOGPIXELSY);
        ReleaseDC(handle, screen);
        NONCLIENTMETRICSW metrics{};
        metrics.cbSize = sizeof(metrics);
        if (SystemParametersInfoW(SPI_GETNONCLIENTMETRICS, sizeof(metrics), &metrics, 0))
            font = CreateFontIndirectW(&metrics.lfMessageFont);

        const auto menu = CreateMenu();
        const auto advanced_menu = CreatePopupMenu();
        AppendMenuW(advanced_menu, MF_STRING, install_exe, L"Install &EXE only");
        AppendMenuW(advanced_menu, MF_STRING, phone_home, L"Disable &Phone Home...");
        AppendMenuW(menu, MF_POPUP, reinterpret_cast<UINT_PTR>(advanced_menu), L"&Advanced");
        const auto help_menu = CreatePopupMenu();
        AppendMenuW(help_menu, MF_STRING, download, L"Download &PatcherGUI...");
        AppendMenuW(help_menu, MF_SEPARATOR, 0, nullptr);
        AppendMenuW(help_menu, MF_STRING, about, L"&About...");
        AppendMenuW(menu, MF_POPUP, reinterpret_cast<UINT_PTR>(help_menu), L"&Help");

        MENUINFO menu_style{};
        menu_style.cbSize = sizeof(menu_style);
        menu_style.fMask = MIM_BACKGROUND;
        menu_style.hbrBack = GetSysColorBrush(COLOR_BTNFACE);
        SetMenuInfo(menu, &menu_style);

        SetMenu(handle, menu);

        control(L"STATIC", L"&Game folder:", 0, 0, 0, 0, 0, game_label);
        game_edit = control(L"EDIT", L"", ES_AUTOHSCROLL | WS_TABSTOP, 0, 0, 0, 0, game);
        SendMessageW(game_edit, EM_SETCUEBANNER, FALSE, reinterpret_cast<LPARAM>(L"XCom-Enemy-Unknown folder"));
        controls.push_back(game_edit);
        controls.push_back(control(L"BUTTON", L"Browse...", WS_TABSTOP, 0, 0, 0, 0, browse_game));
        control(L"STATIC", L"&UPK tools folder:", 0, 0, 0, 0, 0, tools_label);
        tools_edit = control(L"EDIT", L"", ES_AUTOHSCROLL | WS_TABSTOP, 0, 0, 0, 0, tools);
        SendMessageW(tools_edit, EM_SETCUEBANNER, FALSE, reinterpret_cast<LPARAM>(L"PatcherGUI or UPKUtils folder"));
        controls.push_back(tools_edit);
        controls.push_back(control(L"BUTTON", L"Browse...", WS_TABSTOP, 0, 0, 0, 0, browse_tools));
        control(L"STATIC", L"Activity log", 0, 0, 0, 0, 0, log_label);
        output =
            control(L"EDIT", L"", ES_MULTILINE | ES_READONLY | ES_AUTOVSCROLL | WS_VSCROLL | WS_TABSTOP, 0, 0, 0, 0);
        SendMessageW(output, EM_SETLIMITTEXT, 1024 * 1024, 0);

        const std::pair<const wchar_t*, int> buttons[] = {
            {L"&Install", install}, {L"&Restore", restore}, {L"&Status", status}};
        for (const auto& button : buttons)
        {
            controls.push_back(control(L"BUTTON", button.first, WS_TABSTOP, 0, 0, 0, 0, button.second));
        }
        status_bar = control(STATUSCLASSNAMEW, L"", SBARS_SIZEGRIP, 0, 0, 0, 0);
        activity(L"Ready. Close the game before installing or restoring.");
        SetWindowTextW(game_edit, xcom::load_game_directory(installer.app_folder).c_str());
        layout();
    }
};

LRESULT CALLBACK window_proc(HWND handle, UINT message, WPARAM wparam, LPARAM lparam)
{
    auto* window = reinterpret_cast<Window*>(GetWindowLongPtrW(handle, GWLP_USERDATA));
    if (message == WM_NCCREATE)
    {
        window = static_cast<Window*>(reinterpret_cast<CREATESTRUCTW*>(lparam)->lpCreateParams);
        window->handle = handle;
        SetWindowLongPtrW(handle, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(window));
    }
    if (!window)
        return DefWindowProcW(handle, message, wparam, lparam);

    switch (message)
    {
    case WM_CREATE:
        window->create();
        return 0;
    case WM_SIZE:
        window->layout();
        return 0;
    case WM_GETMINMAXINFO:
    {
        auto* limits = reinterpret_cast<MINMAXINFO*>(lparam);
        limits->ptMinTrackSize = {window->pixels(560), window->pixels(320)};
        return 0;
    }
    case WM_CTLCOLORSTATIC:
        if (reinterpret_cast<HWND>(lparam) == window->output)
        {
            const auto dc = reinterpret_cast<HDC>(wparam);
            SetTextColor(dc, GetSysColor(COLOR_WINDOWTEXT));
            SetBkColor(dc, GetSysColor(COLOR_WINDOW));
            return reinterpret_cast<LRESULT>(GetSysColorBrush(COLOR_WINDOW));
        }
        break;
    case WM_COMMAND:
        if (HIWORD(wparam) != BN_CLICKED || window->busy)
            break;
        switch (LOWORD(wparam))
        {
        case browse_game:
            window->browse(window->game_edit);
            break;
        case browse_tools:
            window->browse(window->tools_edit);
            break;
        case install:
            window->start(xcom::Action::install);
            break;
        case restore:
            window->start(xcom::Action::restore);
            break;
        case status:
            window->start(xcom::Action::status);
            break;
        case download:
            ShellExecuteW(handle, L"open", L"https://www.nexusmods.com/xcom/mods/448", nullptr, nullptr, SW_SHOWNORMAL);
            break;
        case install_exe:
            window->start(xcom::Action::install_exe);
            break;
        case phone_home:
            window->start(xcom::Action::phone_home);
            break;
        case about:
            MessageBoxW(handle,
                        L"XCOM: Enemy Within Ultrawide "
                        L"Fix\nVersion " XCOM_VERSION_W L"\n\nCamera, cursor and UI fixes for ultrawide displays.\n"
                        L"For full installation, select a PatcherGUI or UPKUtils folder.\n\n"
                        L"Original project code is licensed under the MIT license.",
                        L"About XCOM EW Ultrawide Fix", MB_OK | MB_ICONINFORMATION);
            break;
        }
        return 0;
    case log_message:
    {
        std::unique_ptr<std::wstring> line(reinterpret_cast<std::wstring*>(lparam));
        window->log(*line);
        return 0;
    }
    case done_message:
    {
        std::unique_ptr<std::wstring> error(reinterpret_cast<std::wstring*>(lparam));
        if (window->worker.joinable())
            window->worker.join();
        window->busy = false;
        window->enable_controls(true);
        window->activity(error->empty() ? L"Ready. Operation completed." : L"Operation failed. See the activity log.");
        if (!error->empty())
            MessageBoxW(handle, error->c_str(), L"XCOM EW Ultrawide Fix", MB_OK | MB_ICONERROR);
        return 0;
    }
    case WM_CLOSE:
        // Do not let a window close interrupt a transaction or destroy its log receiver.
        if (window->busy)
        {
            MessageBoxW(handle, L"Wait for the current operation to finish before closing.", L"XCOM EW Ultrawide Fix",
                        MB_OK);
        }
        else
        {
            window->save();
            DestroyWindow(handle);
        }
        return 0;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(handle, message, wparam, lparam);
}

} // namespace

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE, PWSTR, int show)
{
    const auto com = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    if (FAILED(com))
        return 1;
    SetProcessDPIAware();
    INITCOMMONCONTROLSEX common{sizeof(common), ICC_STANDARD_CLASSES | ICC_BAR_CLASSES};
    InitCommonControlsEx(&common);
    int result = 1;

    try
    {
        Window window;
        WNDCLASSW type{};
        type.lpfnWndProc = window_proc;
        type.hInstance = instance;
        type.lpszClassName = L"XComEWUltrawideFix";
        type.hCursor = LoadCursorW(nullptr, IDC_ARROW);
        type.hIcon = LoadIconW(instance, MAKEINTRESOURCEW(1));
        type.hbrBackground = reinterpret_cast<HBRUSH>(COLOR_BTNFACE + 1);
        if (!RegisterClassW(&type))
            throw std::runtime_error("Cannot register application window");

        const auto screen = GetDC(nullptr);
        window.dpi = GetDeviceCaps(screen, LOGPIXELSY);
        ReleaseDC(nullptr, screen);
        RECT size{0, 0, window.pixels(680), window.pixels(400)};
        const DWORD style = WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN;
        AdjustWindowRect(&size, style, TRUE);
        const auto handle = CreateWindowW(type.lpszClassName, L"XCOM EW Ultrawide Fix v" XCOM_VERSION_W, style,
                                          CW_USEDEFAULT, CW_USEDEFAULT, size.right - size.left, size.bottom - size.top,
                                          nullptr, nullptr, instance, &window);
        if (!handle)
            throw std::runtime_error("Cannot create application window");
        ShowWindow(handle, show);

        MSG message{};
        BOOL next;
        while ((next = GetMessageW(&message, nullptr, 0, 0)) > 0)
        {
            if (!IsDialogMessageW(handle, &message))
            {
                TranslateMessage(&message);
                DispatchMessageW(&message);
            }
        }
        result = next == -1 ? 1 : static_cast<int>(message.wParam);
    }
    catch (const std::exception& error)
    {
        MessageBoxW(nullptr, xcom::from_utf8(error.what()).c_str(), L"XCOM EW Ultrawide Fix", MB_OK | MB_ICONERROR);
    }

    CoUninitialize();
    return result;
}
