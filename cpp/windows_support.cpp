#include "windows_support.hpp"

#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

#include <memory>

namespace xcom {
namespace {

struct HandleCloser {
    void operator()(void* handle) const { if (handle && handle != INVALID_HANDLE_VALUE) CloseHandle(handle); }
};
using Handle = std::unique_ptr<void, HandleCloser>;

// Windows argv parsing doubles backslashes before quotes and the closing quote.
std::wstring quote(const std::wstring& value) {
    std::wstring result = L"\"";
    std::size_t slashes = 0;
    for (wchar_t ch : value) {
        if (ch == L'\\') {
            ++slashes;
        } else {
            result.append(ch == L'"' ? slashes * 2 + 1 : slashes, L'\\');
            result += ch;
            slashes = 0;
        }
    }
    result.append(slashes * 2, L'\\');
    return result + L'"';
}

}

std::wstring from_utf8(const std::string& value) {
    if (value.empty()) return {};
    const auto length = MultiByteToWideChar(CP_UTF8, 0, value.data(), static_cast<int>(value.size()), nullptr, 0);
    std::wstring result(length, L'\0');
    MultiByteToWideChar(CP_UTF8, 0, value.data(), static_cast<int>(value.size()), result.data(), length);
    return result;
}

Path application_folder() {
    std::vector<wchar_t> buffer(32768);
    const auto length = GetModuleFileNameW(nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));
    if (!length || length == buffer.size()) throw std::runtime_error("Cannot locate application directory");
    return Path(std::wstring(buffer.data(), length)).parent_path();
}

void run_windows_tool(const std::vector<Path>& args, const Path& cwd) {
    if (args.empty()) throw std::invalid_argument("Missing tool command");
    std::wstring command;
    for (const auto& arg : args) {
        if (!command.empty()) command += L' ';
        command += quote(arg.wstring());
    }

    // Redirect to disk instead of a pipe: large tool output cannot block the child.
    const auto output_path = cwd / "tool-output.log";
    SECURITY_ATTRIBUTES security{sizeof(SECURITY_ATTRIBUTES), nullptr, TRUE};
    Handle output(CreateFileW(output_path.c_str(), GENERIC_WRITE | GENERIC_READ,
        FILE_SHARE_READ, &security, CREATE_ALWAYS, FILE_ATTRIBUTE_TEMPORARY, nullptr));
    Handle input(CreateFileW(L"NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
        &security, OPEN_EXISTING, 0, nullptr));
    Handle job(CreateJobObjectW(nullptr, nullptr));
    if (output.get() == INVALID_HANDLE_VALUE || input.get() == INVALID_HANDLE_VALUE || !job)
        throw std::runtime_error("Cannot prepare UPK tool process");

    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if (!SetInformationJobObject(job.get(), JobObjectExtendedLimitInformation, &limits, sizeof(limits)))
        throw std::runtime_error("Cannot configure UPK tool process");

    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESTDHANDLES;
    startup.hStdInput = input.get();
    startup.hStdOutput = startup.hStdError = output.get();
    PROCESS_INFORMATION process{};
    if (!CreateProcessW(args.front().c_str(), command.data(), nullptr, nullptr, TRUE,
        CREATE_NO_WINDOW | CREATE_SUSPENDED, nullptr, cwd.c_str(), &startup, &process))
        throw std::runtime_error("Cannot start " + args.front().filename().u8string());

    Handle child(process.hProcess), thread(process.hThread);
    if (!AssignProcessToJobObject(job.get(), child.get())) {
        TerminateProcess(child.get(), 1);
        WaitForSingleObject(child.get(), INFINITE);
        throw std::runtime_error("Cannot supervise UPK tool process");
    }
    if (ResumeThread(thread.get()) == static_cast<DWORD>(-1))
        throw std::runtime_error("Cannot resume UPK tool process");

    const auto wait = WaitForSingleObject(child.get(), 300000);
    if (wait != WAIT_OBJECT_0) {
        TerminateJobObject(job.get(), 1);
        WaitForSingleObject(child.get(), INFINITE);
        throw std::runtime_error("UPK tool timed out or could not be monitored");
    }

    DWORD code = 0;
    if (!GetExitCodeProcess(child.get(), &code)) throw std::runtime_error("Cannot read UPK tool exit code");
    output.reset();
    if (code) {
        const auto bytes = read_file(output_path);
        const auto start = bytes.size() > 3000 ? bytes.size() - 3000 : 0;
        throw std::runtime_error(args.front().filename().u8string() + " failed (" + std::to_string(code)
            + "):\n" + std::string(bytes.begin() + start, bytes.end()));
    }
}

}
