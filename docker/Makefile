FALCON_VERSION=$(shell sudo docker run -it falconry/falcon-bench:py3 python3 -c 'import falcon; import sys; sys.stdout.write(falcon.__version__)')

all: build-benchmark-images

build-benchmark-images:
	sudo docker pull python:3.8-slim
	sudo docker pull python:3.8
	sudo docker pull pypy:3-slim

	sudo docker build --no-cache -t falconry/falcon-bench:${FALCON_VERSION}-py38 -f bench_py3.Dockerfile ./
	sudo docker build --no-cache -t falconry/falcon-bench:${FALCON_VERSION}-py38-cython -f bench_py3_cython.Dockerfile ./
	sudo docker build --no-cache -t falconry/falcon-bench:${FALCON_VERSION}-pypy3 -f bench_pypy3.Dockerfile ./

push:
	sudo docker push falconry/falcon-bench:${FALCON_VERSION}-py38
	sudo docker push falconry/falcon-bench:${FALCON_VERSION}-py38-cython
	sudo docker push falconry/falcon-bench:${FALCON_VERSION}-pypy3
