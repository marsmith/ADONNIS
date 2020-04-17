#called when a search is stalled on a query
#this is done to facilitate the swapping up upstream and downstream searches
QUERY_TERMINATE_CODE = "terminated_on_query"

#when a search runs into the end of a basin
END_OF_BASIN_CODE = "end_of_network"

#could not get or process data
QUERY_FAILURE_CODE = "query_failure"

QUERY_PARSE_FAILURE_CODE = "query_results_parsing_failed"

#we hit the edge of the dataset
EDGE_OF_DATASET_CODE = "edge_of_dataset"

EMPTY_QUERY_CODE = "empty_query_results"

SNAP_FAILURE_CODE = "snap_failure"

failure_codes = [QUERY_TERMINATE_CODE, END_OF_BASIN_CODE, QUERY_FAILURE_CODE, EDGE_OF_DATASET_CODE, QUERY_PARSE_FAILURE_CODE, EMPTY_QUERY_CODE, SNAP_FAILURE_CODE]

def isFailureCode (val):
    if val in failure_codes:
        return True
    else:
        return False