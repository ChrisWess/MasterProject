import {FC} from "react";
import {Box} from "@mui/material";
import {ReactJSXElement} from "@emotion/react/types/jsx-namespace";


interface TabPanelProps {
    children: ReactJSXElement;
    index: number;
    value: number;
}


const TabPanel: FC<TabPanelProps> = ({children, value, index, ...other}) => {

    return <div
        role="tabpanel"
        hidden={value !== index}
        id={'tabpanel-' + index}
        aria-labelledby={'tab-' + index}
        {...other}
    >
        {value === index && <Box sx={{px: 1, pt: 2}}>
            {children}
        </Box>}
    </div>
}

export default TabPanel
