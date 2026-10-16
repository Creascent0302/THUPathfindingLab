
##timestamp, ros time or utc time
float64     timestamp

float64 box_size_x  #size of each box
float64 box_size_y  #size of each box

int16 boxes_num_x   #how many boxes in x
int16 boxes_num_y   #how many boxes in y

float64 map_cx  #ct of the local map
float64 map_cy  #ct of the local map

LocalMap_Element[] local_map