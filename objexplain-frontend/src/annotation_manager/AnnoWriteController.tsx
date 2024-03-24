import {FC, useMemo} from "react";
import {Divider, List, ListItem, ListItemIcon} from "@mui/material";
import Typography from "@mui/material/Typography";
import {DetectedObject} from "../api/models/object";
import {useDispatch, useSelector} from "react-redux";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import {Annotation} from "../api/models/annotation";
import {setSuggestedText} from "../reducers/annotationCreateSlice";


const WriteController: FC = () => {
    const dispatch = useDispatch();
    const annoIdx: number | undefined = useSelector((state: any) => state.annotation.annotationIdx);
    const detObj: DetectedObject | undefined = useSelector((state: any) => state.object.detObj);

    const appendAnnotation = (anno: Annotation) => {
        dispatch(setSuggestedText(anno.text))
    }

    const annoList = useMemo(() => {
        if (annoIdx !== undefined && detObj) {
            let annos = detObj.annotations
            return (<List className="annotations" key="annoList">
                {annos?.filter((_, index) => index !== annoIdx).map((anno, index) =>
                    <ListItemButton key={'annoButt' + index} sx={{py: 0}}
                                    onClick={() => appendAnnotation(anno)}>
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
        return undefined
    }, [annoIdx, detObj])

    return <>
            <Typography variant='h5'>Write or select a full annotation</Typography>
            <Divider/>
            <Typography variant='h6'>Quick-Select one of the below annotations:</Typography>
            {!!annoList && annoList}
        </>
}

export default WriteController
