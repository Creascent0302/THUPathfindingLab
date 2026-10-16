
##timestamp, ros time or utc time
float64     timestamp

##four parts
#part 1: direct commands
int16 	Estop    # 0:none  1:low  2:medium   3:high
bool 	Go       # false, true
int16 	Signal   # 0:none 1:left 2:right

#part 2 -- lane center and drivable area
RefPoint[] refPath


#part 3 -- other setting
int16 mode  #1: attack, 2:dection, 3:transportation
Object[] objects

