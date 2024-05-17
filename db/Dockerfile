FROM postgres:16

WORKDIR /db

RUN apt update && apt install gettext-base
RUN mkdir -p /oracle/pg_data/archive/
RUN chown postgres:postgres /oracle/pg_data/archive/

ARG POSTGRES_USER
ARG DB_PORT
ARG DB_REPL_HOST
ARG DB_REPL_USER
ARG DB_REPL_PASSWORD
ARG DB_DATABASE

COPY ./init.sql .

RUN envsubst < /db/init.sql > /docker-entrypoint-initdb.d/init.sql

RUN cat <<EOF > /etc/postgresql/postgresql.conf
hba_file = '/etc/postgresql/pg_hba.conf'
listen_addresses = '*'
port = ${DB_PORT}
archive_mode = on
archive_command = 'cp %p /oracle/pg_data/archive/%f'
max_wal_senders = 10
wal_level = replica
wal_log_hints = on
log_replication_commands = on
log_destination = 'stderr'
logging_collector = on
log_directory = '/var/log/postgresql/'
log_filename = 'postgresql-16-main.log'
log_timezone = 'Europe/Moscow'
EOF

RUN cat <<EOF > /etc/postgresql/pg_hba.conf
local all ${POSTGRES_USER} peer
host all all 0.0.0.0/0 password
host replication ${DB_REPL_USER} 0.0.0.0/0 scram-sha-256
EOF

ENTRYPOINT [ "bash", "-c", "docker-entrypoint.sh -c config_file=/etc/postgresql/postgresql.conf"]