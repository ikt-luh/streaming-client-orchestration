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

start-experiment COUNT:
	python3 starting_script.py {{COUNT}}