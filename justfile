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

test-csv EXP_DURATION LAMDA CSV_FILE:
	python3 starting_script.py --count 1 --exp-duration {{EXP_DURATION}} --lamda {{LAMDA}} --csv-file {{CSV_FILE}}

test-bandwidth EXP_DURATION LAMDA BANDWIDTH:
	python3 starting_script.py --count 1 --exp-duration {{EXP_DURATION}} --lamda {{LAMDA}} --bandwidth {{BANDWIDTH}}

start-experiment COUNT EXP_DURATION LAMDA:
	python3 starting_script.py --count {{COUNT}} --exp-duration {{EXP_DURATION}} --lamda {{LAMDA}}