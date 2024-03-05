import {BoxProps, Button, Icon, TextField} from "@mui/material";
import Box from "@mui/material/Box";
import SearchIcon from "@mui/icons-material/Search";
import {ChangeEvent, FC, MouseEvent, useState} from "react";


interface ButtonTextfieldProps {
    tfLabel: string
    buttonText: string
    submitFunc: Function
    clearOnSubmit: boolean
    icon?: string | undefined
}

const ButtonTextfield: FC<ButtonTextfieldProps & BoxProps> = ({
                                                                  tfLabel,
                                                                  buttonText,
                                                                  submitFunc,
                                                                  clearOnSubmit,
                                                                  icon,
                                                                  ...props
                                                              }) => {
    const [textInput, setTextInput] = useState<string>("");

    const disabled = textInput?.trim().length == 0;
    let iconElement;
    if (icon == 'search') {
        iconElement = <SearchIcon sx={{color: disabled ? 'text.secondary' : 'darkorange'}}/>
    } else {
        iconElement = <Icon sx={{color: disabled ? 'text.secondary' : 'darkorange'}}>{icon}</Icon>
    }

    const handleTextFieldChange = (event: ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) => {
        event.preventDefault();
        setTextInput(event.target.value);
    }

    const handleInput = (event: MouseEvent<HTMLButtonElement, MouseEvent>) => {
        event.preventDefault();
        submitFunc(textInput.trim());  // Use textFieldInput
        if (clearOnSubmit) {
            setTextInput('');
        }
    }

    return (
        <Box sx={{width: '100%', display: "flex", verticalAlign: "middle"}} {...props}>
            <TextField id="filled-basic"
                       label={tfLabel}
                       size='small'
                       variant="outlined"
                       onChange={(e) => handleTextFieldChange(e)}
                       value={textInput}
                       sx={{
                           mr: '1px', flexGrow: 100,
                           "& .MuiOutlinedInput-notchedOutline": {
                               borderColor: "#9090C0",
                           }
                       }}
            />
            <Button
                variant="outlined"
                onClick={(e: MouseEvent<any, any>) => handleInput(e)}
                disabled={disabled}
                style={{textTransform: "none", width: "fit-content"}}
            >{!!icon ? <>{iconElement}{buttonText}</> : buttonText}</Button>
        </Box>
    );
}

export default ButtonTextfield;
