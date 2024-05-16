FROM postgres:16

WORKDIR /db_repl

ARG DB_REPL_PORT

RUN cat <<EOF > /etc/postgresql/postgresql.conf
listen_addresses = '*'
port = ${DB_REPL_PORT}
log_destination = 'stderr'
logging_collector = on
log_directory = '/var/log/postgresql/'
log_filename = 'postgresql.log'
EOF

RUN rm -rf /var/lib/postgresql/data/*

ENTRYPOINT [ "bash", "-c", "\
sleep 12 \n\
echo ${DB_REPL_PASSWORD} | pg_basebackup -v -R -h ${DB_HOST} -p ${DB_PORT} -U ${DB_REPL_USER} -W -P -D /var/lib/postgresql/data \n\
docker-entrypoint.sh -c config_file=/etc/postgresql/postgresql.conf"]