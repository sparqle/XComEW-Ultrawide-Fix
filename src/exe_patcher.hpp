#pragma once

#include <array>
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

namespace xcom
{

using Bytes = std::vector<std::uint8_t>;

struct Patch
{
    std::string name;
    Bytes original;
    Bytes patched;
};

const std::array<Patch, 3>& patches();

enum class State
{
    clean,
    patched,
    unsupported
};

State inspect(const Bytes& data);
Bytes install(const Bytes& data);
Bytes restore(const Bytes& data);
Bytes disable_phone_home(const Bytes& data);

Bytes read_file(const std::filesystem::path& path);
void write_file_atomic(const std::filesystem::path& path, const Bytes& data);

enum class Operation
{
    install,
    restore,
    disable_phone_home
};

// Validates in memory before backup/write. Dry runs never create a backup.
bool apply_file(const std::filesystem::path& path, Operation operation, bool dry_run);

} // namespace xcom
