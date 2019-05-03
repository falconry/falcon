all: build-benchmark-images

build-benchmark-images:
	sudo docker pull python:3.7-slim
	sudo docker pull python:3.7
	sudo docker pull pypy:3-slim

	sudo docker build -t falconry/falcon-bench:py37 -f bench_py37.Dockerfile ./
	sudo docker build -t falconry/falcon-bench:py37-cython -f bench_py37_cython.Dockerfile ./
	sudo docker build -t falconry/falcon-bench:pypy3 -f bench_pypy3.Dockerfile ./
