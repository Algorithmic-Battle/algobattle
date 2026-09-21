FROM golang:1.21

WORKDIR /algobattle
COPY go.mod *.sum ./
RUN go mod download

COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux go build -o out/

WORKDIR /
CMD ["/algobattle/out/{{ program }}"]
