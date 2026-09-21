FROM debian:12

RUN apt update && apt upgrade
RUN apt install -y clang-15 cmake ninja-build

WORKDIR /algobattle
COPY src src/
ENV CC=/usr/bin/clang-15 CXX=/usr/bin/clang++-15
RUN cmake -S src -B build && cmake --build build --target install

WORKDIR /
CMD ["main"]
