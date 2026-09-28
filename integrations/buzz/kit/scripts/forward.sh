# Sourced: listen on 127.0.0.1:$KIT_PORT in this container and forward to relay:3000 on the Docker network, so
# clients dial ws://localhost:$KIT_PORT and send exactly the Host the relay maps (localhost:$KIT_PORT).
: "${KIT_PORT:?KIT_PORT is not set}"
socat "TCP-LISTEN:$KIT_PORT,bind=127.0.0.1,fork,reuseaddr" TCP:relay:3000 &
for _ in $(seq 50); do (exec 3<>"/dev/tcp/127.0.0.1/$KIT_PORT") 2>/dev/null && break; sleep 0.1; done
