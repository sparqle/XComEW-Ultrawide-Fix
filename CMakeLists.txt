cmake_minimum_required(VERSION 3.21)
project(XComEWUltrawideFix VERSION 2.0.0 LANGUAGES CXX)

if(NOT WIN32)
    message(FATAL_ERROR "The native application requires Windows")
endif()

set(XCOM_VERSION "${PROJECT_VERSION}")
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
option(BUILD_TESTING "Build the native regression tests" OFF)

add_library(xcom_options INTERFACE)
target_include_directories(xcom_options INTERFACE src)
target_compile_features(xcom_options INTERFACE cxx_std_17)
if(MSVC)
    target_compile_options(xcom_options INTERFACE /W4)
elseif(MINGW)
    target_compile_options(xcom_options INTERFACE -Wall -Wextra -Wpedantic)
    target_link_options(xcom_options INTERFACE -static)
    # Resolve the static C++/pthread/CRT dependency cycle together. CLion's
    # pthread library also uses Windows Universal CRT entry points.
    target_link_libraries(xcom_options INTERFACE
        "-Wl,--start-group" stdc++ mingw32 gcc gcc_eh moldname mingwex msvcrt pthread ucrt "-Wl,--end-group")
endif()

if(MINGW)
    get_filename_component(mingw_bin "${CMAKE_CXX_COMPILER}" DIRECTORY)
    find_program(xcom_windres windres HINTS "${mingw_bin}" NO_DEFAULT_PATH REQUIRED)
    set(CMAKE_RC_COMPILER "${xcom_windres}" CACHE FILEPATH "Windows resource compiler" FORCE)
endif()
enable_language(RC)
configure_file(src/app.manifest.in ${CMAKE_CURRENT_BINARY_DIR}/app.manifest @ONLY)
configure_file(src/app.rc.in ${CMAKE_CURRENT_BINARY_DIR}/app.rc @ONLY)

add_executable(native-ui WIN32
    src/app.cpp src/windows_support.cpp src/installer.cpp src/exe_patcher.cpp
    ${CMAKE_CURRENT_BINARY_DIR}/app.rc)
set_target_properties(native-ui PROPERTIES OUTPUT_NAME XComEW-Ultrawide-Fix)
target_link_libraries(native-ui PRIVATE xcom_options ole32 shell32 uuid comctl32)
target_compile_definitions(native-ui PRIVATE UNICODE _UNICODE XCOM_VERSION_W=L"${XCOM_VERSION}")
if(MSVC)
    # The resource file already embeds the application manifest.
    target_link_options(native-ui PRIVATE /MANIFEST:NO)
elseif(MINGW)
    target_link_options(native-ui PRIVATE -municode)
endif()
add_custom_command(TARGET native-ui POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:native-ui>/mods"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/Fix-ultrawide-UI.txt"
        "$<TARGET_FILE_DIR:native-ui>/mods/Fix-ultrawide-UI.txt")

# enable_testing avoids the unused Nightly/Experimental/Continuous dashboard targets.
if(BUILD_TESTING)
    enable_testing()
    add_executable(patcher_tests src/tests/patcher_tests.cpp src/exe_patcher.cpp)
    target_link_libraries(patcher_tests PRIVATE xcom_options)
    add_test(NAME patcher_tests COMMAND patcher_tests)

    add_executable(installer_tests src/tests/installer_tests.cpp src/installer.cpp src/exe_patcher.cpp)
    target_link_libraries(installer_tests PRIVATE xcom_options)
    add_test(NAME installer_tests COMMAND installer_tests)

    add_executable(windows_app_tests
        src/tests/windows_app_tests.cpp src/windows_support.cpp src/installer.cpp src/exe_patcher.cpp)
    target_link_libraries(windows_app_tests PRIVATE xcom_options)
    if(MINGW)
        target_link_options(windows_app_tests PRIVATE -municode)
    endif()
    add_dependencies(windows_app_tests native-ui)
    add_test(NAME windows_app_tests COMMAND windows_app_tests)
    set_tests_properties(windows_app_tests PROPERTIES TIMEOUT 30)
endif()

install(TARGETS native-ui RUNTIME DESTINATION .)
install(FILES mods/Fix-ultrawide-UI.txt DESTINATION mods)
install(FILES README.md LICENSE DESTINATION .)
set(CPACK_GENERATOR ZIP)
set(CPACK_PACKAGE_FILE_NAME "XComEW-Ultrawide-Fix-${XCOM_VERSION}")
set(CPACK_INCLUDE_TOPLEVEL_DIRECTORY OFF)
set(CPACK_PACKAGE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/packages")
set(CPACK_RELEASE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/dist")
set(CPACK_POST_BUILD_SCRIPTS "${CMAKE_CURRENT_SOURCE_DIR}/cmake/copy-release.cmake")
include(CPack)
