#!/bin/bash

# ### Generate pqo anchors
# # List of query IDs
# query_ids=( 1a 2a 3a 4a 16a 17a 18a 20a )

# # Loop through each query ID and run the command
# for query_id in "${query_ids[@]}"; do
#     echo "==========Running query with ID: $query_id=========="
#     python robustness.py --query_id=$query_id --pqo --b=0.5
#     echo "==========Finished query with ID: $query_id=========="
# done

# ### Generate rqo sen_dim for list of querys
# # Directory containing the SQL files
# DIRECTORY="query/join-order-benchmark/rank-by-prob/"

# # Loop through all the SQL files in the directory
# # python robustness.py --query_id=1a --cal_sen=sobol --rqo_query='query/join-order-benchmark/rank-by-prob/1-0-b0.5.sql'      
# for FILE in "$DIRECTORY"*.sql
# do
#   # Extract the base name of the file (without directory path)
#   BASENAME=$(basename "$FILE")

#   # Extract the query_id (first number in the file name)
#   QUERY_ID=$(echo "$BASENAME" | grep -o '^[0-9]*')

#   # b
#   B_NUMBER=$(echo "$BASENAME" | grep -o 'b[0-9.]*' | cut -c2- | sed 's/\.$//')

# #   echo "$B_NUMBER"
#   # Check if the number after 'b' is 0.5
#   if [ "$B_NUMBER" == "0.5" ]; then
#     # Construct the command and execute it
#     CMD="python robustness.py --query_id=${QUERY_ID}a --cal_sen=sobol --rqo_query='$FILE'"
#     echo "Executing: $CMD"
#     eval $CMD
#   fi
# done


# ### Generate rqo results for list of querys
# # Directory containing the SQL files
# DIRECTORY="query/join-order-benchmark/rank-by-prob/"

# # Loop through all the SQL files in the directory
# # python robustness.py --query_id=1a --cal_sen=sobol --rqo_query='query/join-order-benchmark/rank-by-prob/1-0-b0.5.sql'      
# for FILE in "$DIRECTORY"*.sql
# do
#   # Extract the base name of the file (without directory path)
#   BASENAME=$(basename "$FILE")

#   # Extract the query_id (first number in the file name)
#   QUERY_ID=$(echo "$BASENAME" | grep -o '^[0-9]*')

#   # b
#   B_NUMBER=$(echo "$BASENAME" | grep -o 'b[0-9.]*' | cut -c2- | sed 's/\.$//')

# #   echo "$B_NUMBER"
#   # Check if the number after 'b' is 0.5
#   if [ "$B_NUMBER" == "0.5" ]; then
#     # Construct the command and execute it
#     CMD="python robustness.py --query_id=${QUERY_ID}a --rqo_query='$FILE'"
#     echo "Executing: $CMD"
#     eval $CMD
#   fi
# done

### Generate pqo anchors
# List of query IDs
query_ids=( 1a 2a 3a 4a 16a 17a 18a 20a )

# Loop through each query ID and run the command
for query_id in "${query_ids[@]}"; do
    echo "==========Running query with ID: $query_id=========="
    python robustness.py --query_id=$query_id --pqo --b=0.5
    echo "==========Finished query with ID: $query_id=========="
done