import Snackbar from '@mui/material/Snackbar';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';
import MuiAlert, {AlertProps} from '@mui/material/Alert';
import {useParams} from "react-router-dom";
import NotFound from "../utils/NotFound";
import {CircularProgress} from "@mui/material";
import {getRequest} from "../api/requests";
import {forwardRef, SyntheticEvent, useEffect, useState} from "react";
import ObjectPage from "./ObjectPage";


export interface SnackbarMessage {
    message: string;
    key: number;
}

const Alert = forwardRef<HTMLDivElement, AlertProps>(function Alert(
    props,
    ref,
) {
    return <MuiAlert elevation={6} ref={ref} variant="filled" {...props} />;
});

export interface State {
    open: boolean;
    snackPack: readonly SnackbarMessage[];
    messageInfo?: SnackbarMessage;
}

export default function ConsecutiveSnackbars() {
    const [snackPack, setSnackPack] = useState<readonly SnackbarMessage[]>([]);
    const [open, setOpen] = useState(false);
    const [position, setPosition] = useState("bottom" as ("bottom" | "top"));
    const [isAlert, setAlert] = useState(false);
    const [severity, setSeverity] = useState("info" as ("success" | "info" | "warning" | "error"));
    const [messageInfo, setMessageInfo] = useState<SnackbarMessage | undefined>();
    const [render, setRender] = useState(<CircularProgress style={{marginLeft: '50%', marginTop: '20%'}}/>);
    const {projectname} = useParams();

    const callSnackbar = function (message: string, position: "bottom" | "top", type: string) {
        setAlert(false);

        if (type != "normal") {
            setAlert(true);
            setSeverity(type as ("success" | "info" | "warning" | "error"));
        }

        setPosition(position);
        setSnackPack((prev) => [...prev, {message, key: new Date().getTime()}]);
    };

    async function projectExists(pname: string) {
        let data = await getRequest('project/fromUser', pname, {_id: 1})
        if (data) {
            setRender(<ObjectPage/>)
        } else {
            setRender(<NotFound/>)
        }
    }

    useEffect(() => {
        projectname ? projectExists(projectname) : setRender(<NotFound/>);
        if (snackPack.length && !messageInfo) {
            // Set a new snack when we don't have an active one
            setMessageInfo({...snackPack[0]});
            setSnackPack((prev) => prev.slice(1));
            setOpen(true);
        } else if (snackPack.length && messageInfo && open) {
            // Close an active snack when a new one is added
            setOpen(false);
        }
    }, [snackPack, messageInfo, open]);

    const handleClose = (event: SyntheticEvent | Event, reason?: string) => {
        if (reason === 'clickaway') {
            return;
        }
        setOpen(false);
    };

    const handleExited = () => {
        setMessageInfo(undefined);
    };

    if (isAlert) {
        return (
            <div>
                {render}
                <Snackbar
                    key={messageInfo ? messageInfo.key : undefined}
                    open={open}
                    autoHideDuration={6000}
                    onClose={handleClose}
                    TransitionProps={{onExited: handleExited}}
                    anchorOrigin={{horizontal: 'center', vertical: position}}
                    action={
                        <>
                            <IconButton
                                aria-label="close"
                                color="inherit"
                                sx={{p: 0.5}}
                                onClick={handleClose}
                            >
                                <CloseIcon/>
                            </IconButton>
                        </>
                    }>
                    <Alert
                        onClose={handleClose}
                        severity={severity}
                        variant="filled"
                        sx={{width: '100%'}}>
                        {messageInfo ? messageInfo.message : undefined}

                    </Alert>
                </Snackbar>
            </div>
        );
    }
    return (
        <div>
            {render}
            <Snackbar
                key={messageInfo ? messageInfo.key : undefined}
                open={open}
                autoHideDuration={6000}
                onClose={handleClose}
                TransitionProps={{onExited: handleExited}}
                anchorOrigin={{horizontal: 'center', vertical: position}}
                message={messageInfo ? messageInfo.message : undefined}
                action={
                    <>
                        <IconButton
                            aria-label="close"
                            color="inherit"
                            sx={{p: 0.5}}
                            onClick={handleClose}
                        >
                            <CloseIcon/>
                        </IconButton>
                    </>
                }
            />
        </div>
    );
}
