import {FC, SyntheticEvent} from 'react'
import Snackbar from "@mui/material/Snackbar";
import {Alert} from "@mui/material";

interface AlertMessageProps {
    content: string | undefined
    setContent: Function
    severity: any
    displayTime: number
}

const AlertMessage: FC<AlertMessageProps> = ({content, setContent, severity, displayTime}) => {

    const handleClose = (event?: SyntheticEvent | Event, reason?: string) => {
        if (reason === 'clickaway') {
            return;
        }

        setContent(undefined);
    };

    return (
        <div>
            <Snackbar open={!!content} autoHideDuration={displayTime} onClose={handleClose}>
                <Alert
                    onClose={handleClose}
                    severity={severity}
                    variant="filled"
                    sx={{width: '100%'}}
                >
                    {content}
                </Alert>
            </Snackbar>
        </div>
    );
}

export default AlertMessage;
