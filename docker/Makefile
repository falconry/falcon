all: build-benchmark-images

build-benchmark-images:
	sudo docker build -t falconry/falcon-bench:py27-pip -f bench_py27_pip.Dockerfile ./
	sudo docker build -t falconry/falcon-bench:py35-pip -f bench_py35_pip.Dockerfile ./
	sudo docker build -t falconry/falcon-bench:pypy2-pip -f bench_pypy2_pip.Dockerfile ./
