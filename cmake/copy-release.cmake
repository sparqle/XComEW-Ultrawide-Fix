# CPack stages under the build directory; only completed archives belong in dist.
file(MAKE_DIRECTORY "${CPACK_RELEASE_DIRECTORY}")
foreach(archive IN LISTS CPACK_PACKAGE_FILES)
    file(COPY "${archive}" DESTINATION "${CPACK_RELEASE_DIRECTORY}")
endforeach()
