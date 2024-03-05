import * as React from 'react';
import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Toolbar from '@mui/material/Toolbar';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import Menu from '@mui/material/Menu';
import MenuIcon from '@mui/icons-material/Menu';
import HomeIcon from '@mui/icons-material/Home';
import Container from '@mui/material/Container';
import Avatar from '@mui/material/Avatar';
import Button from '@mui/material/Button';
import Tooltip from '@mui/material/Tooltip';
import MenuItem from '@mui/material/MenuItem';
import {Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle} from "@mui/material";
import {getRequest} from "../api/requests";
import {useSelector} from "react-redux";
import {useLoadUser} from "../utils/Hooks";

const pages = ['Help', 'GitHub'];
const settings = ['Dashboard', 'Project', 'Logout'];

const ResponsiveAppBar = () => {
    const [anchorElNav, setAnchorElNav] = React.useState<null | HTMLElement>(null);
    const [anchorElUser, setAnchorElUser] = React.useState<null | HTMLElement>(null);
    const [open, setOpen] = React.useState(false);

    useLoadUser();
    // global state (redux)
    const userInfo = useSelector((state: any) => state.user.value);
    const title = useSelector((state: any) => state.appBar.title);

    const helpContent =
        <DialogContent>
            <DialogContentText>
                Welcome to the ObjeXplain-App. Here are some instructions to help you.
            </DialogContentText>
            <DialogTitle>Get started:</DialogTitle>
            <DialogContentText>
                First you will need to upload a document. You can do this in the block on the right by
                swtiching to the <b>documents</b>-tab. Alternatively you can simply write your own text in
                the <b>textfield</b>.
                Just click on <i>upload</i> or <i>submit</i> to send it to the neural network. The neural network is
                designed to annotate german text.
                After your submission the annotated document will appear in the middle block, sentence by sentence.
            </DialogContentText>
            <DialogTitle>Coreference information:</DialogTitle>
            <DialogContentText>
                Each color + number represents an entity. You can click on an annotated word to see other
                appearances of that entity on the left block. Further, if it is an annotation made by the neural network
                you can see its confidence
                values if you switch to the <b>statistics</b>-tab on the right block. In the <b>search</b>-tab you can
                look for words and letter combinations.
            </DialogContentText>
            <DialogTitle>Editing yourself:</DialogTitle>
            <DialogContentText>
                You can use the editing functions to edit the annotation made by the neural network.
                Simply highlight words with your mouse by clicking and dragging. The words will be highlighted in a
                bright blue color and
                appear in the window on the left block. Now you can use the buttons on the left block to add an
                annotation the your selected words. If
                that is too slow for you, you can use shortcuts.
            </DialogContentText>
            <DialogTitle>Shortcuts:</DialogTitle>
            <DialogContentText>
                The shortcuts are activated by pressing and releasing the <i>a</i>-key.Select words, press and
                hold <i>a</i> and use any of the following combinations:
                <br/>
                <br/>
                <b><i>your number</i></b>: The selected words will be annotated as instance of coref-entity nr.<i>your
                number</i>.
                <br/>
                <br/>
                <b><i>n</i></b>: The selected words will be annotated as instance of a new coref-entity.
                <br/>
                <br/>
                <b><i>c</i></b>: If the selected words are an instance of coref-entity nr. x, you copy x.
                <br/>
                <br/>
                <b><i>v</i></b>: If you already copied coref-entity nr. x, the selected words will be annotated as
                instance of coref-entity nr.x.
                <br/>
                <br/>
                <b><i>d</i></b>: If the selected words are an instance of a coref-entity, that annotation will be
                deleted.
                <br/>
                <br/>
                After typing your input, release <i>a</i>.
            </DialogContentText>
            <DialogTitle>Other shortcuts:</DialogTitle>
            <DialogContentText>
                <b><i>Ctrl + s</i></b>: Save current changes made to the document.
                <br/>
                <br/>
                <b><i>Ctrl + f</i></b>: Switch to the <b>search</b>-tab
            </DialogContentText>
        </DialogContent>

    function handlePage(page: string) {
        console.log("Pressed " + page + "-button")
        switch (page) {
            case "Logout":
                getRequest('logout')
                window.location.href = 'http://localhost:5000/login'
                break;
            case "Dashboard":
                window.location.href = 'http://localhost:3000/Dashboard'
                break;
            case "Project":
                window.location.href = 'http://localhost:3000/Project'  // TODO: switch to currently selected project or go to dashboard if none selected
                break;
            case "Help":
                handleOpen()
                break;
            case "GitHub":
                window.open("https://github.com/ChrisWess/...");
                break;

        }
    }

    const handleOpen = () => {
        setOpen(true);
    };

    const handleClose = () => {
        setOpen(false);
    };

    const handleOpenNavMenu = (event: React.MouseEvent<HTMLElement>) => {
        setAnchorElNav(event.currentTarget);
    };
    const handleOpenUserMenu = (event: React.MouseEvent<HTMLElement>) => {
        setAnchorElUser(event.currentTarget);
    };

    const handleCloseNavMenu = () => {
        setAnchorElNav(null);
    };

    const handleCloseUserMenu = () => {
        setAnchorElUser(null);
    };

    return (
        <AppBar position="static">
            <Container maxWidth="xl">
                <Toolbar disableGutters>
                    <Box sx={{flexGrow: 1, display: {xs: 'flex', md: 'none'}}}>
                        <IconButton
                            size="large"
                            aria-label="account of current user"
                            aria-controls="menu-appbar"
                            aria-haspopup="true"
                            onClick={handleOpenNavMenu}
                            color="inherit"
                        >
                            <MenuIcon/>
                        </IconButton>
                        <Menu
                            id="menu-appbar"
                            anchorEl={anchorElNav}
                            anchorOrigin={{
                                vertical: 'bottom',
                                horizontal: 'left',
                            }}
                            keepMounted
                            transformOrigin={{
                                vertical: 'top',
                                horizontal: 'left',
                            }}
                            open={Boolean(anchorElNav)}
                            onClose={handleCloseNavMenu}
                            sx={{
                                display: {xs: 'block', md: 'none'},
                            }}
                        >
                            {pages.map((page) => (
                                <MenuItem key={page} onClick={handleCloseNavMenu}>
                                    <Typography textAlign="center">{page}</Typography>
                                </MenuItem>
                            ))}
                        </Menu>
                    </Box>
                    <Dialog open={open} onClose={handleClose}>
                        <DialogTitle>Help</DialogTitle>
                        {helpContent}
                        <DialogActions>
                            <Button onClick={handleClose}>Cancel</Button>
                        </DialogActions>
                    </Dialog>

                    <Box sx={{flexGrow: 1, display: {xs: 'none', md: 'flex'}}}>
                        <IconButton sx={{color: 'text.secondary'}} onClick={() => handlePage('Dashboard')}>
                            <HomeIcon/>
                        </IconButton>
                        {pages.map((page) => (
                            <Button
                                key={page}
                                onClick={() => handlePage(page)}
                                sx={{my: 2, color: 'white', display: 'block'}}
                            >
                                {page}
                            </Button>
                        ))}
                    </Box>

                    <Typography
                        variant="h5"
                        noWrap
                        component="a"
                        href=""
                        sx={{
                            mr: '6%',
                            display: {xs: 'flex', md: 'flex'},
                            flexGrow: 1,
                            fontWeight: 700,
                            letterSpacing: '.1rem',
                            color: 'inherit',
                            textDecoration: 'none',
                            textShadow: '1px 1px #00AAFF'
                        }}
                    >
                        {title}
                    </Typography>

                    <Box sx={{flexGrow: 0}}>
                        <Tooltip title="Open settings menu">
                            <IconButton onClick={handleOpenUserMenu} sx={{p: 0}}>
                                <Avatar sx={{bgcolor: userInfo ? userInfo.color : 'grey', border: '1px solid #878787'}}
                                        alt={userInfo && userInfo.name ? userInfo.name : "User Icon"}
                                        src="todo"/>
                            </IconButton>
                        </Tooltip>
                        <Menu
                            sx={{mt: '45px'}}
                            id="menu-appbar"
                            anchorEl={anchorElUser}
                            anchorOrigin={{
                                vertical: 'top',
                                horizontal: 'right',
                            }}
                            keepMounted
                            transformOrigin={{
                                vertical: 'top',
                                horizontal: 'right',
                            }}
                            open={Boolean(anchorElUser)}
                            onClose={handleCloseUserMenu}
                        >
                            {settings.map((setting) => (
                                <MenuItem key={setting} onClick={handleCloseUserMenu}>
                                    <Typography textAlign="center" onClick={() => handlePage(setting)}>
                                        {setting}
                                    </Typography>
                                </MenuItem>
                            ))}
                        </Menu>
                    </Box>

                </Toolbar>
            </Container>
        </AppBar>
    );
};
export default ResponsiveAppBar;
