CORES=$(nproc)

while true
do
    CPU_LIMIT=$(echo "(100 / ($CORES * 3))" | bc -l | awk '{print int($1)}')
    LOWER_LIMIT=$(echo "$CPU_LIMIT * 0.25" | bc -l | awk '{print int($1)}')

    STATS=$(docker stats --no-stream --format "{{.Container}}:{{.CPUPerc}}" | sed 's/%//')
    
    echo "$STATS" | while IFS= read line
    do
        IFS=: read CONTAINER USAGE <<< $line;
        USAGE=$(echo $USAGE | awk '{print int($1)}')

        if [[ $USAGE -gt $CPU_LIMIT ]]; then
            curl http://10.114.0.2/api/monitor -d "container=$CONTAINER"
        elif [[ $USAGE -lt $LOWER_LIMIT ]]; then
            curl http://10.114.0.2/api/monitor -d "container=$CONTAINER" -X "DELETE"
        fi
    done
done