import {FC, useState} from "react";
import {Outlet} from "react-router-dom";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import {ReactJSXElement} from "@emotion/react/types/jsx-namespace";


const ProjectLayout: FC = () => {
    const [controlPanel, setControlPanel] = useState<ReactJSXElement>();

    return (
        <Box className="project-layout" sx={{height: 830, maxHeight: 830}}>
            <Grid container spacing={2} sx={{ml: "1%", mt: "0.5%", width: "97%", height: '100%'}}>
                <Grid item xs={4} md={4} lg={4} sx={{maxHeight: '100%'}}>
                    <Paper elevation={6} sx={{p: 2, height: '100%'}}>
                        {controlPanel}
                    </Paper>
                </Grid>
                <Grid item xs={8} md={8} lg={8} sx={{height: '100%'}}>
                    <Paper elevation={6} sx={{pt: 2, px: 2, height: '100%'}}>
                        <Outlet context={{controlPanel, setControlPanel}}/>
                    </Paper>
                </Grid>
            </Grid>
        </Box>
    )
}

export default ProjectLayout
