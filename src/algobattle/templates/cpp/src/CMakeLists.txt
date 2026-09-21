cmake_minimum_required(VERSION 3.1...3.27)

project(
  ModernCMakeExample
  VERSION 1.0
  LANGUAGES CXX
)

add_executable(main main.cpp)

install(TARGETS main DESTINATION "")
