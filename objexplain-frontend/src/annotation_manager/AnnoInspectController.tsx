import {FC, useMemo} from "react";
import {Button, List, ListItem, ListItemIcon} from "@mui/material";
import Typography from "@mui/material/Typography";
import ListItemText from "@mui/material/ListItemText";
import {useDispatch, useSelector} from "react-redux";
import {Annotation} from "../api/models/annotation";
import LabelIcon from "@mui/icons-material/Label";
import {CONCEPT_COLORS} from "./AnnotationView";
import {postRequest} from "../api/requests";
import {useNavigate} from "react-router-dom";
import {DetectedObject} from "../api/models/object";


const AnnoInspectController: FC = () => {
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const annotation: Annotation | undefined = useSelector((state: any) => state.newAnno.newAnnotation);
    const conceptRanges: [number, number][] | undefined = useSelector((state: any) => state.newAnno.conceptRanges);
    const detObj: DetectedObject | undefined = useSelector((state: any) => state.object.detObj);

    const selectedConcepts = useMemo(() => {
        return (<List className="selectedConcepts" key="conceptList"
                      sx={{bgcolor: '#252525', p: 0, maxHeight: '430px', overflow: 'auto'}}>
            {annotation?.concepts && conceptRanges && annotation.concepts.map((concept, index) => {
                let range = conceptRanges[index]
                let conceptSub = annotation.tokens.slice(range[0], range[1] + 1)
                    .filter(value => value.length > 1).join(' ')
                return <ListItem divider key={'conceptItem' + index}>
                    <ListItemIcon sx={{color: 'text.secondary', mr: 2}} key={'conceptIcon' + index}>
                        <LabelIcon sx={{color: CONCEPT_COLORS[index % 10], mr: 2}}/>
                    </ListItemIcon>
                    <ListItemText key={'conceptText' + index}>
                        <Typography variant='h6' color='primary.light'>
                            <b>{conceptSub}</b>
                        </Typography>
                        <Typography variant='subtitle2' color='primary.light'>
                            <b>{concept.phraseWords.join(' ')}</b> ({concept.phraseIdxs.toString()})
                        </Typography>
                        <Typography variant='subtitle2' color='primary.light'>
                            Created at: {concept.createdAt}
                        </Typography>
                    </ListItemText>
                </ListItem>
            })}
        </List>)
    }, [annotation])

    const pushAnnotationEntity = () => {
        if (detObj) {
            let annoEntity = {...annotation}
            delete annoEntity.concepts
            delete annoEntity.createdAt
            delete annoEntity.updatedAt
            postRequest('annotation/full', {annotation: annoEntity, objectId: detObj._id})
                .then(data => {
                    if (data) {
                        console.log(data)
                        // TODO: put annotation into idoc list => dispatch(setDoc())
                        navigate('TODO')
                    }
                })
        }
    }

    return <>
        <Typography variant='h5'>Inspect and verify/finalize your new annotation</Typography>
        <Typography variant='subtitle1'>Show list of concepts here and show the highlighted annotation
            in the lower right panel. You may also switch back to the other tabs to adjust and resubmit
            the annotation.
        </Typography>
        <Button sx={{width: '100%', height: '40px', my: 2, fontSize: '12pt'}} variant='contained'
                onClick={pushAnnotationEntity}>
            <b>Finalize Annotation</b>
        </Button>
        {selectedConcepts}
    </>
}

export default AnnoInspectController
