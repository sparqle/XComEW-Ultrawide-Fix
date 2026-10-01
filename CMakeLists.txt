cmake_minimum_required(VERSION 3.20)
project(XComEWUltrawideFix VERSION 1.2.0 LANGUAGES CXX)

add_library(xcom_patch cpp/exe_patcher.cpp)
target_include_directories(xcom_patch PUBLIC cpp)
target_compile_features(xcom_patch PUBLIC cxx_std_17)
if(MSVC)
    target_compile_options(xcom_patch PRIVATE /W4)
else()
    target_compile_options(xcom_patch PRIVATE -Wall -Wextra -Wpedantic)
endif()
add_executable(xcomew-patcher cpp/main.cpp)
target_link_libraries(xcomew-patcher PRIVATE xcom_patch)

add_library(xcom_installer cpp/installer.cpp)
target_link_libraries(xcom_installer PUBLIC xcom_patch)
if(MSVC)
    target_compile_options(xcom_installer PRIVATE /W4)
else()
    target_compile_options(xcom_installer PRIVATE -Wall -Wextra -Wpedantic)
endif()

if(WIN32)
    enable_language(RC)
    configure_file(cpp/app.rc.in ${CMAKE_CURRENT_BINARY_DIR}/app.rc @ONLY)
    add_executable(XComEW-Ultrawide-Fix WIN32
        cpp/app.cpp cpp/windows_support.cpp ${CMAKE_CURRENT_BINARY_DIR}/app.rc)
    target_link_libraries(XComEW-Ultrawide-Fix PRIVATE xcom_installer ole32 shell32 uuid comctl32)
    target_compile_definitions(XComEW-Ultrawide-Fix PRIVATE
        UNICODE _UNICODE XCOM_VERSION_W=L"${PROJECT_VERSION}")
    add_custom_command(TARGET XComEW-Ultrawide-Fix POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:XComEW-Ultrawide-Fix>/mods"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${CMAKE_CURRENT_SOURCE_DIR}/mods/Fix-ultrawide-UI.txt"
            "$<TARGET_FILE_DIR:XComEW-Ultrawide-Fix>/mods/Fix-ultrawide-UI.txt")
    if(MSVC)
        target_compile_options(XComEW-Ultrawide-Fix PRIVATE /W4)
        # The resource file already embeds the application manifest.
        target_link_options(XComEW-Ultrawide-Fix PRIVATE /MANIFEST:NO)
    else()
        target_compile_options(XComEW-Ultrawide-Fix PRIVATE -Wall -Wextra -Wpedantic)
    endif()
    if(MINGW)
        target_link_options(XComEW-Ultrawide-Fix PRIVATE -municode)
        get_filename_component(mingw_bin "${CMAKE_CXX_COMPILER}" DIRECTORY)
        file(GLOB mingw_runtime_dlls
            "${mingw_bin}/libgcc_s_*.dll"
            "${mingw_bin}/libstdc++-6.dll"
            "${mingw_bin}/libwinpthread-1.dll")
        foreach(runtime_dll IN LISTS mingw_runtime_dlls)
            add_custom_command(TARGET XComEW-Ultrawide-Fix POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    "${runtime_dll}" "$<TARGET_FILE_DIR:XComEW-Ultrawide-Fix>")
        endforeach()
        install(FILES ${mingw_runtime_dlls} DESTINATION .)
    endif()

    install(TARGETS XComEW-Ultrawide-Fix xcomew-patcher RUNTIME DESTINATION .)
    install(FILES mods/Fix-ultrawide-UI.txt DESTINATION mods)
    install(FILES README.md LICENSE DESTINATION .)
    if(MSVC)
        include(InstallRequiredSystemLibraries)
    endif()
    set(CPACK_GENERATOR ZIP)
    set(CPACK_PACKAGE_FILE_NAME "XComEW-Ultrawide-Fix-${PROJECT_VERSION}")
    set(CPACK_INCLUDE_TOPLEVEL_DIRECTORY OFF)
    include(CPack)
endif()

if(MINGW)
    target_link_options(xcomew-patcher PRIVATE -municode)
endif()

include(CTest)
if(BUILD_TESTING)
    add_executable(patcher_tests cpp/tests/patcher_tests.cpp)
    target_link_libraries(patcher_tests PRIVATE xcom_patch)
    add_test(NAME patcher_tests COMMAND patcher_tests)

    add_executable(installer_tests cpp/tests/installer_tests.cpp)
    target_link_libraries(installer_tests PRIVATE xcom_installer)
    add_test(NAME installer_tests COMMAND installer_tests)

    if(WIN32)
        add_executable(windows_app_tests cpp/tests/windows_app_tests.cpp cpp/windows_support.cpp)
        target_link_libraries(windows_app_tests PRIVATE xcom_installer)
        add_dependencies(windows_app_tests XComEW-Ultrawide-Fix)
        if(MINGW)
            target_link_options(windows_app_tests PRIVATE -municode)
        endif()
        add_test(NAME windows_app_tests COMMAND windows_app_tests)
        set_tests_properties(windows_app_tests PROPERTIES TIMEOUT 30)
    endif()
endif()
