import {FC, useMemo} from "react";
import {Box, Button} from "@mui/material";
import {buildAnnotation} from "./AnnotationView";
import {useDispatch, useSelector} from "react-redux";
import {Annotation} from "../api/models/annotation";


interface AnnotationInspectorProps {
    index: number;
    value: number;
}


const AnnotationInspector: FC<AnnotationInspectorProps> = ({value, index, ...other}) => {

    const dispatch = useDispatch();
    const annotation: Annotation | undefined = useSelector((state: any) => state.newAnno.newAnnotation);
    const conceptRanges: [number, number][] | undefined = useSelector((state: any) => state.newAnno.conceptRanges);

    const newlyProcessedAnno = useMemo(() => {
        if (annotation && conceptRanges) {
            let result = buildAnnotation(annotation, conceptRanges, [],
                true, false, () => {
                })
            return result[0]
        }
        return undefined
    }, [annotation, conceptRanges])

    return <div
        hidden={value !== index}
        id={'anno-writer'}
        aria-labelledby={'anno-writer'}
        style={{width: '1000px'}}
        {...other}
    >
        {value === index && <Box sx={{p: 1}}>
            {!!newlyProcessedAnno && newlyProcessedAnno}
            <Button>Finalize Annotation</Button>
        </Box>}
    </div>
}

export default AnnotationInspector
