import * as React from "react";
import CircularProgress, {CircularProgressProps,} from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";

const CircularProgressWithLabel: React.FC<CircularProgressProps> = (props: CircularProgressProps) => {
    let value = Math.round(100 * props.value!)
    return (
        <Box sx={{position: "relative", display: "inline-flex"}}>
            <CircularProgress
                variant="determinate"
                size={50}
                thickness={5}
                value={Math.min(value, 99.5)}
                color='secondary'
            />
            <Box
                sx={{
                    top: 3,
                    left: 3,
                    bottom: 0,
                    right: 0,
                    position: "absolute",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                }}
            >
                <Typography
                    variant="caption"
                    component="div"
                    color="text.secondary"
                >{`${value}%`}</Typography>
            </Box>
        </Box>
    );
}

export default CircularProgressWithLabel
