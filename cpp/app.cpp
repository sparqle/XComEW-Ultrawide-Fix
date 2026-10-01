#include "windows_support.hpp"

#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <commctrl.h>
#include <shlobj.h>

#include <memory>
#include <thread>

namespace {

constexpr UINT log_message = WM_APP + 1;
constexpr UINT done_message = WM_APP + 2;
enum Control { game = 100, tools, browse_game, browse_tools, install, restore, status, advanced, download };

struct Window {
    HWND handle = nullptr;
    HWND game_edit = nullptr;
    HWND tools_edit = nullptr;
    HWND output = nullptr;
    HFONT font = nullptr;
    HFONT title_font = nullptr;
    std::vector<HWND> controls;
    std::thread worker;
    bool busy = false;
    xcom::Installer installer{xcom::application_folder(), xcom::run_windows_tool};

    ~Window() {
        if (worker.joinable()) worker.join();
        if (font) DeleteObject(font);
        if (title_font) DeleteObject(title_font);
    }

    HWND control(const wchar_t* type, const wchar_t* label, DWORD style,
                 int x, int y, int width, int height, int id = 0) {
        const auto child = CreateWindowExW(type == std::wstring(L"EDIT") ? WS_EX_CLIENTEDGE : 0,
            type, label, WS_CHILD | WS_VISIBLE | style, x, y, width, height, handle,
            reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)), GetModuleHandleW(nullptr), nullptr);
        SendMessageW(child, WM_SETFONT, reinterpret_cast<WPARAM>(font), TRUE);
        return child;
    }

    static std::wstring text(HWND edit) {
        std::wstring value(GetWindowTextLengthW(edit) + 1, L'\0');
        GetWindowTextW(edit, value.data(), static_cast<int>(value.size()));
        value.resize(value.size() - 1);
        const auto first = value.find_first_not_of(L" \t\r\n");
        return first == std::wstring::npos ? L"" : value.substr(first, value.find_last_not_of(L" \t\r\n") - first + 1);
    }

    void log(const std::wstring& message) {
        const auto line = message + L"\r\n";
        SendMessageW(output, EM_SETSEL, static_cast<WPARAM>(-1), static_cast<LPARAM>(-1));
        SendMessageW(output, EM_REPLACESEL, FALSE, reinterpret_cast<LPARAM>(line.c_str()));
        SendMessageW(output, EM_SCROLLCARET, 0, 0);
    }

    void save() {
        try { xcom::save_game_directory(installer.app_folder, xcom::Path(text(game_edit))); }
        catch (const std::exception& error) { log(L"Could not save folder: " + xcom::from_utf8(error.what())); }
    }

    void browse(HWND edit) {
        IFileOpenDialog* dialog = nullptr;
        if (FAILED(CoCreateInstance(CLSID_FileOpenDialog, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&dialog))))
            return;
        DWORD options = 0;
        dialog->GetOptions(&options);
        dialog->SetOptions(options | FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM);
        dialog->SetTitle(edit == game_edit ? L"Select XCom-Enemy-Unknown folder" : L"Select PatcherGUI or UPKUtils folder");
        if (SUCCEEDED(dialog->Show(handle))) {
            IShellItem* item = nullptr;
            if (SUCCEEDED(dialog->GetResult(&item))) {
                PWSTR path = nullptr;
                if (SUCCEEDED(item->GetDisplayName(SIGDN_FILESYSPATH, &path))) {
                    SetWindowTextW(edit, path);
                    CoTaskMemFree(path);
                }
                item->Release();
            }
        }
        dialog->Release();
        if (edit == game_edit) save();
    }

    void start(xcom::Action action) {
        if (busy) return;
        try {
            const auto base = xcom::find_game_directory(xcom::Path(text(game_edit)));
            if (base.empty()) throw std::invalid_argument("Could not locate XCOM. Select your XCom-Enemy-Unknown folder.");
            SetWindowTextW(game_edit, base.c_str());
            xcom::executable_location(base);
            save();
            xcom::Path binaries;
            if (installer.needs_tools(action)) {
                const auto selected = text(tools_edit);
                binaries = xcom::binaries_folder(selected.empty() ? installer.app_folder / "third_party" : xcom::Path(selected));
            }

            if (action == xcom::Action::phone_home) {
                const auto bytes = xcom::read_file(xcom::executable_location(base));
                if (xcom::disable_phone_home(bytes) == bytes) {
                    log(L"Phone home already disabled: xcm.invalid");
                    return;
                }
                if (MessageBoxW(handle, L"Replace the phone home address with xcm.invalid?\n\n"
                    L"PatcherGUI's yiraxis.com is now registered. The .invalid domain is reserved. Close the game first.",
                    L"Disable Phone Home", MB_YESNO | MB_ICONQUESTION | MB_DEFBUTTON2) != IDYES) return;
            }

            if (worker.joinable()) worker.join();
            busy = true;
            for (const auto child : controls) EnableWindow(child, FALSE);
            log(L"Working...");
            try {
                worker = std::thread([this, action, base, binaries] {
                    std::wstring failure;
                    const auto post = [&](const std::string& line) {
                        auto value = std::make_unique<std::wstring>(xcom::from_utf8(line));
                        if (PostMessageW(handle, log_message, 0, reinterpret_cast<LPARAM>(value.get()))) value.release();
                    };
                    try {
                        installer.execute(action, base, binaries, post);
                        post("Done.");
                    } catch (const std::exception& error) {
                        failure = xcom::from_utf8(error.what());
                        post(std::string("Error: ") + error.what());
                    }
                    auto value = std::make_unique<std::wstring>(failure);
                    if (PostMessageW(handle, done_message, 0, reinterpret_cast<LPARAM>(value.get()))) value.release();
                });
            } catch (...) {
                busy = false;
                for (const auto child : controls) EnableWindow(child, TRUE);
                throw;
            }
        } catch (const std::exception& error) {
            MessageBoxW(handle, xcom::from_utf8(error.what()).c_str(), L"XCOM EW Ultrawide Fix", MB_OK | MB_ICONERROR);
        }
    }

    void create() {
        font = CreateFontW(-16, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
            OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI");
        title_font = CreateFontW(-23, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
            OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI");
        const auto title = control(L"STATIC", L"XCOM: Enemy Within - Ultrawide Fix - v" XCOM_VERSION_W, 0, 16, 16, 725, 32);
        SendMessageW(title, WM_SETFONT, reinterpret_cast<WPARAM>(title_font), TRUE);

        control(L"STATIC", L"XCom-Enemy-Unknown Folder", 0, 16, 67, 218, 24);
        game_edit = control(L"EDIT", L"", ES_AUTOHSCROLL | WS_TABSTOP, 236, 62, 410, 28, game);
        controls.push_back(game_edit);
        controls.push_back(control(L"BUTTON", L"Browse...", WS_TABSTOP, 656, 62, 88, 28, browse_game));
        control(L"STATIC", L"UPK tools folder", 0, 16, 107, 218, 24);
        tools_edit = control(L"EDIT", L"", ES_AUTOHSCROLL | WS_TABSTOP, 236, 102, 410, 28, tools);
        controls.push_back(tools_edit);
        controls.push_back(control(L"BUTTON", L"Browse...", WS_TABSTOP, 656, 102, 88, 28, browse_tools));
        control(L"STATIC", L"Select PatcherGUI or UPKUtils, containing DecompressLZO.exe and PatchUPK.exe.", 0, 16, 144, 725, 24);
        controls.push_back(control(L"BUTTON", L"Download PatcherGUI", WS_TABSTOP, 16, 176, 185, 28, download));

        const std::pair<const wchar_t*, int> buttons[] = {
            {L"Install", install}, {L"Restore", restore}, {L"Status", status}, {L"Advanced", advanced}};
        int x = 16;
        for (const auto& button : buttons) {
            controls.push_back(control(L"BUTTON", button.first, WS_TABSTOP, x, 220, 112, 32, button.second));
            x += 124;
        }
        output = control(L"EDIT", L"", ES_MULTILINE | ES_READONLY | ES_AUTOVSCROLL | WS_VSCROLL | WS_TABSTOP,
            16, 270, 728, 180);
        SendMessageW(output, EM_SETLIMITTEXT, 1024 * 1024, 0);
        SetWindowTextW(game_edit, xcom::load_game_directory(installer.app_folder).c_str());
    }
};

LRESULT CALLBACK window_proc(HWND handle, UINT message, WPARAM wparam, LPARAM lparam) {
    auto* window = reinterpret_cast<Window*>(GetWindowLongPtrW(handle, GWLP_USERDATA));
    if (message == WM_NCCREATE) {
        window = static_cast<Window*>(reinterpret_cast<CREATESTRUCTW*>(lparam)->lpCreateParams);
        window->handle = handle;
        SetWindowLongPtrW(handle, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(window));
    }
    if (!window) return DefWindowProcW(handle, message, wparam, lparam);

    switch (message) {
    case WM_CREATE:
        window->create();
        return 0;
    case WM_COMMAND:
        if (HIWORD(wparam) != BN_CLICKED || window->busy) break;
        switch (LOWORD(wparam)) {
        case browse_game: window->browse(window->game_edit); break;
        case browse_tools: window->browse(window->tools_edit); break;
        case install: window->start(xcom::Action::install); break;
        case restore: window->start(xcom::Action::restore); break;
        case status: window->start(xcom::Action::status); break;
        case download:
            ShellExecuteW(handle, L"open", L"https://www.nexusmods.com/xcom/mods/448", nullptr, nullptr, SW_SHOWNORMAL);
            break;
        case advanced: {
            const auto menu = CreatePopupMenu();
            AppendMenuW(menu, MF_STRING, 1, L"Install EXE only");
            AppendMenuW(menu, MF_STRING, 2, L"Disable Phone Home");
            RECT rect{};
            GetWindowRect(GetDlgItem(handle, advanced), &rect);
            const auto selected = TrackPopupMenu(menu, TPM_RETURNCMD, rect.left, rect.bottom, 0, handle, nullptr);
            DestroyMenu(menu);
            if (selected) window->start(selected == 1 ? xcom::Action::install_exe : xcom::Action::phone_home);
            break;
        }
        }
        return 0;
    case log_message: {
        std::unique_ptr<std::wstring> line(reinterpret_cast<std::wstring*>(lparam));
        window->log(*line);
        return 0;
    }
    case done_message: {
        std::unique_ptr<std::wstring> error(reinterpret_cast<std::wstring*>(lparam));
        if (window->worker.joinable()) window->worker.join();
        window->busy = false;
        for (const auto child : window->controls) EnableWindow(child, TRUE);
        if (!error->empty()) MessageBoxW(handle, error->c_str(), L"XCOM EW Ultrawide Fix", MB_OK | MB_ICONERROR);
        return 0;
    }
    case WM_CLOSE:
        // Do not let a window close interrupt a transaction or destroy its log receiver.
        if (window->busy) {
            MessageBoxW(handle, L"Wait for the current operation to finish before closing.", L"XCOM EW Ultrawide Fix", MB_OK);
        } else {
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

}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE, PWSTR, int show) {
    const auto com = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    if (FAILED(com)) return 1;
    INITCOMMONCONTROLSEX common{sizeof(common), ICC_STANDARD_CLASSES};
    InitCommonControlsEx(&common);
    int result = 1;

    try {
        Window window;
        WNDCLASSW type{};
        type.lpfnWndProc = window_proc;
        type.hInstance = instance;
        type.lpszClassName = L"XComEWUltrawideFix";
        type.hCursor = LoadCursorW(nullptr, IDC_ARROW);
        type.hIcon = LoadIconW(instance, MAKEINTRESOURCEW(1));
        type.hbrBackground = reinterpret_cast<HBRUSH>(COLOR_BTNFACE + 1);
        if (!RegisterClassW(&type)) throw std::runtime_error("Cannot register application window");

        RECT size{0, 0, 760, 470};
        const DWORD style = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX;
        AdjustWindowRect(&size, style, FALSE);
        const auto handle = CreateWindowW(type.lpszClassName, L"XCOM EW Ultrawide Fix v" XCOM_VERSION_W,
            style, CW_USEDEFAULT, CW_USEDEFAULT, size.right - size.left, size.bottom - size.top,
            nullptr, nullptr, instance, &window);
        if (!handle) throw std::runtime_error("Cannot create application window");
        ShowWindow(handle, show);

        MSG message{};
        BOOL next;
        while ((next = GetMessageW(&message, nullptr, 0, 0)) > 0) {
            if (!IsDialogMessageW(handle, &message)) {
                TranslateMessage(&message);
                DispatchMessageW(&message);
            }
        }
        result = next == -1 ? 1 : static_cast<int>(message.wParam);
    } catch (const std::exception& error) {
        MessageBoxW(nullptr, xcom::from_utf8(error.what()).c_str(), L"XCOM EW Ultrawide Fix", MB_OK | MB_ICONERROR);
    }

    CoUninitialize();
    return result;
}
