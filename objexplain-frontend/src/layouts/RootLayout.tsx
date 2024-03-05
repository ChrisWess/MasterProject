import React from "react";
import ResponsiveAppBar from "./ResponsiveAppBar";
import {ThemeProvider} from "@emotion/react";
import {createTheme} from "@mui/material/styles";
import {Outlet} from "react-router-dom";
import Box from "@mui/material/Box";
import CssBaseline from "@mui/material/CssBaseline";
import {Link, Typography} from "@mui/material";


const theme = createTheme({
    palette: {
        primary: {
            main: '#f57c00',
            // light: will be calculated from palette.primary.main,
            // dark: will be calculated from palette.primary.main,
            contrastText: '#fff'
        },
        secondary: {
            main: '#00D4EE',
            //light: '#F5EBFF',
            dark: '#0f68f7',
            contrastText: 'rgba(255, 255, 255, 0.2)',
        },
        background: {
            default: '#191919',
            paper: '#1d2021',
        },
        divider: 'rgba(255, 255, 255, 0.12)',
        text: {
            primary: '#fff',
            secondary: 'rgba(255, 255, 255, 0.5)',
        },
    },
});


function Copyright(props: any) {
    return (
        <Typography variant="body2" color="secondary.contrastText" align="center" {...props}>
            {'Copyright © '}
            <Link color="inherit" href="https://mui.com/">
                ObjeXplain App
            </Link>{' '}
            {new Date().getFullYear()}
            {'.'}
        </Typography>
    );
}


const RootLayout: React.FC = () => {
    return (
        <ThemeProvider theme={theme}>
            <CssBaseline/>
            <Box className="root-layout">
                <ResponsiveAppBar></ResponsiveAppBar>
                <main>
                    <Outlet/>
                </main>
            </Box>
            <Copyright sx={{pt: 2.4}}/>
        </ThemeProvider>
    )
}

export default RootLayout
