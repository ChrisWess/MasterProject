import {FC} from "react";
import {Box, Button} from "@mui/material";
import {TextareaAutosize as BaseTextareaAutosize} from '@mui/base/TextareaAutosize';
import {styled} from '@mui/system';
import {blue, grey} from "@mui/material/colors";
import {useDispatch, useSelector} from "react-redux";
import {Annotation} from "../api/models/annotation";


const Textarea = styled(BaseTextareaAutosize)(
    ({theme}) => `
    box-sizing: border-box;
    width: 320px;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.875rem;
    font-weight: 400;
    line-height: 1.5;
    padding: 8px 12px;
    border-radius: 8px;
    color: ${theme.palette.mode === 'dark' ? grey[300] : grey[900]};
    background: ${theme.palette.mode === 'dark' ? grey[900] : '#fff'};
    border: 1px solid ${theme.palette.mode === 'dark' ? grey[700] : grey[200]};
    box-shadow: 0px 2px 2px ${theme.palette.mode === 'dark' ? grey[900] : grey[50]};

    &:hover {
      border-color: ${blue[400]};
    }

    &:focus {
      border-color: ${blue[400]};
      box-shadow: 0 0 0 3px ${theme.palette.mode === 'dark' ? blue[600] : blue[200]};
    }

    // firefox
    &:focus-visible {
      outline: 0;
    }
  `,
);


interface AnnotationWriterProps {
    index: number;
    value: number;
}


const AnnotationWriter: FC<AnnotationWriterProps> = ({value, index, ...other}) => {

    const dispatch = useDispatch();
    const annotation: Annotation | undefined = useSelector((state: any) => state.newAnno.newAnnotation);
    const conceptRanges: [number, number][] | undefined = useSelector((state: any) => state.newAnno.conceptRanges);

    return <div
        hidden={value !== index}
        id={'anno-writer'}
        aria-labelledby={'anno-writer'}
        style={{width: '1000px'}}
        {...other}
    >
        {value === index && <Box sx={{p: 1}}>
            <Textarea aria-label="annotation textarea" minRows={3}
                      sx={{minWidth: '100%', maxWidth: '100%', maxHeight: 100, minHeight: 60}}
                      placeholder="Write your annotation by describing all characteristics of the shown object"/>
            <Button sx={{width: '30%', float: 'right'}} onClick={() => {
                // TODO: submit annotation to backend, write result into newAnnotation state and
                //   then switch state to AnnotationViewer (modeId = 2)
            }}>Submit Annotation</Button>
        </Box>}
    </div>
}

export default AnnotationWriter
