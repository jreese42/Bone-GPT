cmake_minimum_required(VERSION 3.6)

project(BoneGPT)

enable_testing()

# Find Python and Virtualenv. We don't actually use the output of the
# find_package, but it'll give nicer errors.
find_package(Python3 REQUIRED)
find_program(VIRTUALENV virtualenv)

find_program(PIPER_PATH piper)
if (NOT PIPER_PATH)
    message(FATAL_ERROR "Unable to locate piper on PATH.\n"
    "See https://github.com/rhasspy/piper")
endif()
configure_file(.config.in .config @ONLY)

if(NOT VIRTUALENV)
    message(FATAL_ERROR "Could not find `virtualenv` in PATH")
endif()
set(VIRTUALENV ${VIRTUALENV} -p python3)

# Generate the virtualenv and ensure it's up to date.
add_custom_command(
    OUTPUT .venv
    COMMAND ${VIRTUALENV} .venv
)
add_custom_command(
    OUTPUT .venv.requirements
    DEPENDS .venv requirements.txt
    COMMAND ${CMAKE_COMMAND} -E copy ${CMAKE_CURRENT_SOURCE_DIR}/requirements.txt requirements.txt
    COMMAND ./.venv/bin/pip install -r requirements.txt --upgrade
)

# Build command line to run py.test.
set(PYTEST
    ${CMAKE_CURRENT_BINARY_DIR}/.venv/bin/python2
    ${CMAKE_CURRENT_BINARY_DIR}/.venv/bin/py.test
)

add_custom_target(Tests ALL
    DEPENDS .venv.requirements
    SOURCES requirements.txt
)

add_test(NAME run_tests
    COMMAND ${PYTEST} ${CMAKE_CURRENT_SOURCE_DIR}/test_sample.py
)