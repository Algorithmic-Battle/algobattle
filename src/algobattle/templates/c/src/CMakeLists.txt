cmake_minimum_required(VERSION 3.1...3.27)

project(
  ModernCMakeExample
  VERSION 1.0
  LANGUAGES C
)

add_executable(main main.c)

install(TARGETS main DESTINATION "")
