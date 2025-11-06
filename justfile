PLAYER_IMAGE := "pyrabbit-player"
DOCKER_TAG := "latest"

build-player:
	docker build -t {{PLAYER_IMAGE}}:{{DOCKER_TAG}} .
	docker tag {{PLAYER_IMAGE}}:{{DOCKER_TAG}} player-base:{{DOCKER_TAG}}

start-player ID:
	docker compose -f docker-compose.player.yaml -p istream_player_{{ID}} up -d \
	--no-build \
	--no-recreate \
	--remove-orphans

test-player:
	docker compose -f docker-compose.player.yaml run --rm --service-ports --entrypoint /bin/sh istream_player

create-network:
	docker network create expnet

start-experiment CONFIG_PATH:
	python3 run_experiment.py --config {{CONFIG_PATH}} 

download-bw-traces:
	wget https://github.com/uccmisl/5Gdataset/raw/refs/heads/master/5G-production-dataset.zip && \
	unzip 5G-production-dataset.zip && \
	rm 5G-production-dataset.zip 


clean:
    docker ps --format '\{\{.Names\}\}' \
      | grep -E 'istream_player_|switch_' \
      | xargs -r docker rm -f
