import {FC, useEffect, useMemo} from "react";
import {Box, Divider, List, ListItem, ListItemIcon} from "@mui/material";
import Typography from "@mui/material/Typography";
import {DetectedObject} from "../api/models/object";
import {useDispatch, useSelector} from "react-redux";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import {Annotation} from "../api/models/annotation";
import {initAnnoSelectionFlags, markAnnoSelected, setSuggestedText} from "../reducers/annotationCreateSlice";


const WriteController: FC = () => {
    const dispatch = useDispatch();
    const detObj: DetectedObject | undefined = useSelector((state: any) => state.object.detObj);
    const annosUsed: boolean[] | undefined = useSelector((state: any) => state.newAnno.annosSelected);
    const suggestedText: string | undefined = useSelector((state: any) => state.newAnno.suggestedText);

    const appendAnnotation = (anno: Annotation, index: number) => {
        dispatch(setSuggestedText(anno.text))
        dispatch(markAnnoSelected(index))
    }

    const annoList = useMemo(() => {
        if (annosUsed && detObj) {
            let annos = detObj.annotations
            return (<List className="annotations" key="annoList" sx={{bgcolor: '#252525'}}>
                {annos?.map((anno, index) =>
                    <ListItemButton key={'annoButt' + index} sx={{py: 0}} disabled={annosUsed[index]}
                                    onClick={() => appendAnnotation(anno, index)}>
                        <ListItem divider key={'annoItem' + index}>
                            <ListItemIcon sx={{color: 'text.secondary', width: '10px'}} key={'annoIcon' + index}>
                                {index + 1}
                            </ListItemIcon>
                            <ListItemText key={'annoText' + index}>
                                <Typography variant='inherit' color='primary.light'>
                                    {anno.text}
                                </Typography>
                            </ListItemText>
                        </ListItem>
                    </ListItemButton>)}
            </List>)
        }
        return <></>
    }, [annosUsed, detObj])

    useEffect(() => {
        if (detObj?.annotations && suggestedText === undefined) {
            dispatch(initAnnoSelectionFlags(detObj.annotations.length))
        }
    }, [detObj, suggestedText]);

    // TODO: allow saving how often an annotation has been selected in "Text Writer". Use a weighted random
    //  selection for annotations to show the users, weighted by the number of selections, given the type of object.
    // TODO: Add another list that contains suggested annotations from an AI, that gets the object image as input.

    return <>
        <Typography variant='h6'>Write or select a full annotation</Typography>
        <Divider sx={{my: 1}}/>
        <Typography variant='subtitle1' sx={{mb: 2}}>Quick-Select one of the below annotations:</Typography>
        <Box sx={{height: '350px', overflow: 'auto', border: '3px solid', borderColor: '#161616'}}>
            {annoList}
        </Box>
    </>
}

export default WriteController
