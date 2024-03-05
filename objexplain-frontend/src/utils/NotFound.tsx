import React from 'react';
import {ThemeProvider, useTheme} from '@mui/material/styles';
import {Box} from "@mui/material";
import CssBaseline from "@mui/material/CssBaseline";
import Container from "@mui/material/Container";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import {Link} from "react-router-dom";


const NotFound: React.FC<{}> = ({}) => {
    const theme = useTheme();
    return (
        <ThemeProvider theme={theme}>
            <Box sx={{ display: 'flex' }}>
                <CssBaseline />
                <Box
                    component="main"
                    sx={{
                        backgroundColor: "#e6e6e6",
                        flexGrow: 1,
                        height: '100vh',
                        overflow: 'auto',
                    }}
                >
                    <Container maxWidth="xl" sx={{ mt: 4, mb: 4, marginTop: "100pt"}}>


                        <Grid container spacing={3} rowSpacing={3} sx={{marginLeft: "auto", marginRight: "auto", width: '200pt', float: "center"}}>
                            <Grid item xs={12} md={12} lg={12}>
                                <Paper
                                    elevation={20}
                                    sx={{
                                        p: 2,
                                        display: 'flex',
                                        flexDirection: 'column',
                                        height: 'auto',
                                        overflow: 'auto',
                                        float: 'center',
                                        textAlign: 'center',
                                        fontSize: "16pt", 
                                        backgroundColor: "#white"
                                    }}>
                                    Nothing over here!
                                    <Link style={{backgroundColor: "#1976d2", borderRadius: '10px', boxShadow: '0 4px 8px 0 rgba(0, 0, 0, 0.2)', textAlign: 'center'}} to="/dashboard">Send me home</Link>
                                </Paper>
                            </Grid>
                        </Grid>
                    </Container>
                </Box>
            </Box>
        </ThemeProvider>
    );
}

export default NotFound;
