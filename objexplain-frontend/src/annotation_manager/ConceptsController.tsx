import {FC, useEffect, useMemo, useState} from "react";
import {Box, Divider, List, ListItem, ListItemIcon} from "@mui/material";
import Typography from "@mui/material/Typography";
import {Concept} from "../api/models/concept";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import AddIcon from "@mui/icons-material/Add";
import {getRequest, postRequest} from "../api/requests";
import {CorpusWord} from "../api/models/corpus";
import PhraseChip from "./PhraseChip";
import ButtonTextfield from "../components/ButtonTextfield";
import {useDispatch} from "react-redux";
import {addAdjective, addFullConcept, addNoun} from "../reducers/annotationCreateSlice";
import Button from "@mui/material/Button";


export const loadSuggestedConcepts = async () => {
    // TODO: temporary functionality for testing frontend (true impl should suggest based on selected object)
    return await getRequest('concept', undefined, {limit: 10})
}


export const loadSuggestedAdjectives = async () => {
    // TODO: temporary functionality for testing frontend
    return await getRequest('corpus/adjective', undefined, {limit: 10})
}


export const loadSuggestedNouns = async () => {
    // TODO: temporary functionality for testing frontend
    return await getRequest('corpus/noun', undefined, {limit: 10})
}


const ConceptsController: FC = () => {
    const [selectedConceptIdx, setSelectedConceptIdx] = useState<number>();
    const [conceptsUsed, setConceptsUsed] = useState<boolean[]>();
    const [concepts, setConcepts] = useState<Concept[]>();
    const [adjectives, setAdjectives] = useState<CorpusWord[]>();
    const [nouns, setNouns] = useState<CorpusWord[]>();

    const dispatch = useDispatch();

    const submitConceptClick = () => {
        if (selectedConceptIdx !== undefined && concepts && conceptsUsed && !conceptsUsed[selectedConceptIdx]) {
            dispatch(addFullConcept(concepts[selectedConceptIdx]))
            let usedConcepts = [...conceptsUsed];
            usedConcepts[selectedConceptIdx] = true;
            setConceptsUsed(usedConcepts);
            setSelectedConceptIdx(undefined);
        }
    }

    const suggestedConcepts = useMemo(() => {
        return (<List className="suggestedConcepts" key="suggestionList">
            {concepts && conceptsUsed && concepts.map((concept, index) =>
                <ListItem divider key={'concSelectItem' + index}>
                    <ListItemButton key={'concSelectButt' + index} sx={{py: 0}}
                                    onClick={() => setSelectedConceptIdx(index)}
                                    disabled={conceptsUsed[index]}>
                        <ListItemIcon sx={{color: 'text.secondary', mr: 2}} key={'concSelectIcon' + index}>
                            {index + 1}
                        </ListItemIcon>
                        <ListItemText key={'concSelectText' + index}>
                            <Typography variant='h6' color='primary.light'>
                                <b>{concept.phraseWords.join(' ')}</b>
                            </Typography>
                        </ListItemText>
                        <ListItemIcon>
                            <AddIcon sx={{color: 'text.primary'}}/>
                        </ListItemIcon>
                    </ListItemButton>
                </ListItem>)}
            <ListItemButton key={'conceptLoader'} sx={{py: 0, height: '65px'}} onClick={() => {}}>
                    <ListItem divider key={'conceptLoadItem'} sx={{height: '65px'}}>
                        <ListItemIcon sx={{color: 'text.secondary', mr: 2}} key={'conceptLoadIcon'}>
                            <AddIcon/>
                        </ListItemIcon>
                        <ListItemText key={'conceptLoadText'}>
                            <Typography variant='h6' color='primary.light'>
                                Load more Concepts
                            </Typography>
                        </ListItemText>
                    </ListItem>
                </ListItemButton>
        </List>)
    }, [concepts])

    const handleChipClick = (word: CorpusWord) => {
        let input = [word.text, word.index]
        word.nounFlag ? dispatch(addNoun(input)) : dispatch(addAdjective(input))
    }

    const customSubmitFactory = (isNoun: boolean) => {
        return (text: string) => {
            postRequest('corpus', {word: text, isNoun: isNoun}).then(data => {
                if (data) {
                    let result: CorpusWord = data.result
                    let input = [result.text, result.index]
                    isNoun ? dispatch(addNoun(input)) : dispatch(addAdjective(input))
                }
            })
        }
    }

    const suggestedAdjectives = useMemo(() => {
        return <Box sx={{bgcolor: 'gray', width: '100%'}}>
                <Typography variant='h6'>Select suggested adjectives:</Typography>
                {adjectives && adjectives.map(word => <PhraseChip token={word.text}
                                                                  phraseIdx={word.index} isNoun={false}
                                                                  handleClick={() => handleChipClick(word)}/>)}
                <ButtonTextfield tfLabel='Custom Adjective' buttonText='Add' submitFunc={customSubmitFactory(false)} clearOnSubmit />
            </Box>
    }, [adjectives])

    const suggestedNouns = useMemo(() => {
        return <Box sx={{bgcolor: 'gray', width: '100%'}}>
                <Typography variant='h6'>Select suggested nouns:</Typography>
                {nouns && nouns.map(word => <PhraseChip token={word.text}
                                                        phraseIdx={word.index} isNoun={true}
                                                        handleClick={() => handleChipClick(word)}/>)}
                <ButtonTextfield tfLabel='Custom Noun' buttonText='Add' submitFunc={customSubmitFactory(true)} clearOnSubmit />
            </Box>
    }, [nouns])

    useEffect(() => {
        loadSuggestedConcepts().then(data => {
            if (data) {
                let result = data.result;
                setConceptsUsed(Array(result.length).fill(false))
                setConcepts(result)
            }
        })
        loadSuggestedAdjectives().then(data => data && setAdjectives(data.result))
        loadSuggestedNouns().then(data => data && setNouns(data.result))
    }, []);

    return <>
            <Typography variant='h5'>Select suggested Concepts or build new ones</Typography>
            <Divider/>
            <Typography variant='h6'>Choose suggested, already existing concepts:</Typography>
            {suggestedConcepts}
            <Button sx={{textTransform: 'none'}} onClick={submitConceptClick}>Add Concept to your Annotation</Button>
            <Divider/>
            <Typography variant='h6'>Build a custom concept:</Typography>
            <Typography variant='subtitle1'>Select or create at least one adjective and at least one noun
                from the Panels below.
                The current work-in-progress concept is shown at the last list entry at the lower right
                panel.</Typography>
            {suggestedAdjectives}
            <Divider/>
            {suggestedNouns}
        </>
}

export default ConceptsController
