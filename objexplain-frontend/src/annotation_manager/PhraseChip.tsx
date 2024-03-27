import {FC} from "react";
import Tooltip from "@mui/material/Tooltip";
import {Chip} from "@mui/material";


interface PhraseChipProps {
    token: string;
    phraseIdx: number;
    isNoun: boolean;
    handleClick?: any;
    handleDelete?: any;
}


const PhraseChip: FC<PhraseChipProps> = ({token, phraseIdx, isNoun, handleClick, handleDelete}) => {
    token = isNoun ? token.charAt(0).toUpperCase() + token.substring(1).toLowerCase() : token.toLowerCase()
    return <Tooltip title={'phrase word ' + phraseIdx}>
        <Chip label={token} variant="outlined" color={isNoun ? 'primary' : 'success'}
              onClick={handleClick} onDelete={handleDelete} sx={{m: '2px'}}/>
    </Tooltip>
}

export default PhraseChip