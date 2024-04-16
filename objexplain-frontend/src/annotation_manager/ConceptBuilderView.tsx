import {FC, useMemo} from "react";
import {Box, Button, IconButton, List, ListItem, ListItemIcon} from "@mui/material";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import {useDispatch, useSelector} from "react-redux";
import {
    clearConcepts,
    removeAdjectiveAt,
    removeNounAt,
    removeSelectedConcept,
    setConceptEditIdx,
    setMode,
    setNewAnnotation,
    switchAdj,
    switchNoun
} from "../reducers/annotationCreateSlice";
import PhraseChip from "./PhraseChip";
import {getRequest} from "../api/requests";
import {Label} from "../api/models/label";
import DeleteIcon from "@mui/icons-material/Delete";
import {DragDropContext, Draggable} from 'react-beautiful-dnd';
import StrictModeDroppable from "../components/StrictModeDroppable";


interface ConceptBuilderProps {
    index: number;
    value: number;
    setAlertContent: Function;
    setAlertSeverity: Function;
}


const ConceptBuilderView: FC<ConceptBuilderProps> = ({value, index, setAlertContent, setAlertSeverity, ...other}) => {
    const dispatch = useDispatch();
    const objectLabel: Label | undefined = useSelector((state: any) => state.object.objectLabel);
    const concAdjectives: string[][] = useSelector((state: any) => state.newAnno.adjectives);
    const concNouns: string[][] = useSelector((state: any) => state.newAnno.nouns);
    const adjectiveIdxs: number[][] = useSelector((state: any) => state.newAnno.adjectiveIdxs);
    const nounIdxs: number[][] = useSelector((state: any) => state.newAnno.nounIdxs);
    const conceptIdx: number = useSelector((state: any) => state.newAnno.conceptEditIdx);

    const unselectedListElement = (tokens: string[], index: number) => {
        return <ListItem divider key={'concItem' + index} sx={{py: 0}}>
            <ListItemIcon key={'concIcon' + index} sx={{color: 'text.secondary', width: '10px', pl: 2}}>
                {index + 1}
            </ListItemIcon>
            <ListItemButton key={'concButt' + index} onClick={() => dispatch(setConceptEditIdx(index))}>
                <ListItemText key={'concText' + index}>
                    <Typography key={'concTextInner' + index} variant='inherit' color='primary.light'>
                        {tokens.join(' ') + ' ' + concNouns[index].join(' ')}
                    </Typography>
                </ListItemText>
            </ListItemButton>
            <IconButton aria-label="comment" onClick={() => dispatch(removeSelectedConcept(index))} sx={{pr: 3.4}}>
                <DeleteIcon sx={{color: 'text.secondary'}}/>
            </IconButton>
        </ListItem>
    }

    const onDragEnd = (result: any) => {
        if (!result.destination) return;

        let sourceIdx = result.source.index
        let destIdx = result.destination.index
        let adjs = concAdjectives[conceptIdx];
        let maxIdx: number
        let isNoun: boolean
        if (sourceIdx >= adjs.length) {
            let nouns = concNouns[conceptIdx];
            isNoun = true
            sourceIdx = sourceIdx - adjs.length
            destIdx = destIdx - adjs.length
            maxIdx = nouns.length - 1
        } else {
            isNoun = false
            maxIdx = adjs.length - 1
        }
        if (destIdx < 0) {
            destIdx = 0
        } else if (destIdx > maxIdx) {
            destIdx = maxIdx
        }
        if (isNoun) {
            dispatch(switchNoun([sourceIdx, destIdx]))
        } else {
            dispatch(switchAdj([sourceIdx, destIdx]))
        }
    };

    const conceptList = useMemo(() => {
        return (<List className="concepts" key="conceptList" sx={{p: 0}}>
            {!!conceptIdx && concAdjectives.slice(0, conceptIdx).map((adjectives, index) =>
                unselectedListElement(adjectives, index))}
            {concAdjectives.length > 0 && concNouns.length > 0 && (
                <ListItem divider key={'concEditItem'} sx={{color: 'white', minHeight: '50px', maxWidth: '96%', ml: 2}}>
                    <ListItemIcon key={'concEditIcon'} sx={{color: 'text.secondary'}}>
                        {conceptIdx + 1}
                    </ListItemIcon>
                    <DragDropContext onDragEnd={onDragEnd}>
                        <StrictModeDroppable droppableId='concept-chips' direction='horizontal' type='chips'>
                            {(provided) => (
                                <Box sx={{width: '100%', maxWidth: '100%', display: 'flex', flexWrap: 'wrap'}}
                                     ref={provided.innerRef} {...provided.droppableProps}>
                                    {concAdjectives[conceptIdx].map(
                                        (token, index) => <Draggable key={'dragAdj' + index}
                                                                     draggableId={'dragAdj' + index}
                                                                     index={index}>
                                            {(provided) => (<div
                                                {...provided.draggableProps}
                                                {...provided.dragHandleProps}
                                                ref={provided.innerRef}>
                                                <PhraseChip key={'concChip' + index}
                                                            token={token}
                                                            phraseIdx={adjectiveIdxs[conceptIdx][index]}
                                                            isNoun={false}
                                                            handleDelete={() => dispatch(removeAdjectiveAt(index))}/>
                                            </div>)}
                                        </Draggable>)}
                                    {concNouns[conceptIdx].map(
                                        (token, index) => <Draggable key={'dragNoun' + index}
                                                                     draggableId={'dragNoun' + index}
                                                                     index={concAdjectives[conceptIdx].length + index}>
                                            {(provided) => (<div
                                                {...provided.draggableProps}
                                                {...provided.dragHandleProps}
                                                ref={provided.innerRef}>
                                                <PhraseChip key={'concChip' + index}
                                                            token={token}
                                                            phraseIdx={nounIdxs[conceptIdx][index]}
                                                            isNoun={true}
                                                            handleDelete={() => dispatch(removeNounAt(index))}/>
                                            </div>)}
                                        </Draggable>)}
                                    {provided.placeholder}
                                </Box>)}
                        </StrictModeDroppable>
                    </DragDropContext>
                    <IconButton aria-label="comment" onClick={() => dispatch(removeSelectedConcept(conceptIdx))}>
                        <DeleteIcon sx={{color: 'text.secondary'}}/>
                    </IconButton>
                </ListItem>)}
            {concAdjectives.slice(conceptIdx + 1).map((adjectives, index) => {
                index = index + conceptIdx + 1;
                return unselectedListElement(adjectives, index);
            })}
        </List>)
    }, [concAdjectives, concNouns, adjectiveIdxs, nounIdxs, conceptIdx])

    const submitAnnotationConcepts = () => {
        let unfinishedIdxs = adjectiveIdxs
            .map((adjIdxArr, index) => adjIdxArr.length && nounIdxs[index].length ? null : index)
            .filter(value => value !== null)
        if (unfinishedIdxs.length) {
            dispatch(setConceptEditIdx(unfinishedIdxs[0]!))
            setAlertSeverity('warning')
            if (unfinishedIdxs.length == 1) {
                setAlertContent('There is an unfinished concept definition with only adjectives, only nouns or no words at all!')
            } else {
                setAlertContent(`There are ${unfinishedIdxs.length} unfinished concept definitions with only adjectives, only nouns or no words at all!`)
            }
        } else if (objectLabel?.categories) {
            let idxs: number[][] = adjectiveIdxs
                .map((adjIdxArr, index) => [...adjIdxArr, ...nounIdxs[index]])
                .filter(arr => arr.length)
            let category = objectLabel.categories[0];
            getRequest('annotation/fromIdxs', undefined,
                {corpusIdxs: JSON.stringify(idxs), category: category}).then(data => {
                if (data) {
                    dispatch(setNewAnnotation(data.result));
                    dispatch(setMode(2));
                }
            })
        }
    }

    return <div
        hidden={value !== index}
        id={'concept-builder'}
        aria-labelledby={'concept-builder'}
        style={{width: '900px'}}
        {...other}
    >
        {value === index && <Box sx={{height: '280px', p: 1}}>
            <Box sx={{display: 'flex', justifyContent: 'space-between', alignContent: 'center'}}>
                <Typography variant='h6'>List of chosen Concepts:</Typography>
                <Box width='60%'>
                    <Button sx={{width: '50%'}} onClick={() => dispatch(clearConcepts())}>Clear all Concepts</Button>
                    <Button sx={{width: '50%'}} onClick={submitAnnotationConcepts} disabled={!adjectiveIdxs.length}>
                        Build Annotation
                    </Button>
                </Box>
            </Box>
            <Box sx={{height: '230px', border: '3px solid', borderColor: '#203020', overflow: 'auto'}}>
                {conceptList}
            </Box>
        </Box>}
    </div>
}

export default ConceptBuilderView
