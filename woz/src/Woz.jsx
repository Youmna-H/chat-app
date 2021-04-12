import React, { useState } from 'react';
import ReactDOM from "react-dom";
import { useParams } from 'react-router';
import "./index.css";
import "bootstrap/dist/css/bootstrap.min.css";
import "shards-ui/dist/css/shards.min.css";
import { BrowserRouter, Route, Switch } from 'react-router-dom'
import {
    Container,
    Row,
    Col,
    Button,
    FormSelect,
    FormCheckbox,
    FormRadio
} from "shards-react";
import {
    ApolloClient,
    InMemoryCache,
    ApolloProvider,
    ApolloProviderHooks,
    useSubscription,
    useQuery,
    useMutation,
    gql,
} from "@apollo/client";
import { WebSocketLink } from "@apollo/client/link/ws";
import Chat from 'chat/Chat'; //chat is the remote name of the client

const link = new WebSocketLink({
    uri: `ws://localhost:4000/`,
    options: {
        reconnect: true,
    },
});
const client = new ApolloClient({
    link,
    uri: 'http://localhost:4000/',
    cache: new InMemoryCache()
});

const GET_MESSAGES = gql`
  subscription {
    messages {
      id
      user
      content
    }
  }
`;


const GET_RESPONSE = gql`
    query GetResponse($usermessage: String!, $model:String, $num_responses:Int, $classify: Int,
         $utt: String, $dataset: String, $data_type: String, $response: String) {
    wozCandidateResponses(usermessage: $usermessage, model: $model, num_responses: $num_responses,
         classify: $classify, utt: $utt, dataset: $dataset, data_type: $data_type, response: $response)
      {
        relevance,
        content,
        stance
      }
  }`;

const SELECT_TOPIC = gql`
  mutation($id: String!) {
    selectTopic(id: $id)
  }
`;

const GET_TOPIC = gql`
  subscription {
    currentTopic {
      id
      topic
      text
    }
  }
`;


const CandidateResponseContainer = ({ usermessage, model, num_responses, classify, utt, dataset, data_type, response }) => {
    const { loading, error, data } = useQuery(GET_RESPONSE, {
        variables: {
            usermessage: usermessage, model: model, num_responses: parseInt(num_responses),
            classify: classify === true ? 1 : 0, utt: utt, dataset: dataset, data_type: data_type, response: response
        },
    });
    if (loading) return <div>Loading...</div>;
    if (error) return <div>Error! ${error.message}</div>;
    var color_codes = { "pro": "green", "con": "red", "neutral": "blue" }

    if (classify) {
        var pro_responses = data.wozCandidateResponses.filter(obj => obj.stance === 'pro');
        var con_responses = data.wozCandidateResponses.filter(obj => obj.stance === 'con');
        var neutral_responses = data.wozCandidateResponses.filter(obj => obj.stance === 'neutral');
        return (
            <div>
                <label>Pro</label>
                {pro_responses.length > 0 ?
                    <ol>
                        {
                            pro_responses.map(item => <li key={item.relevance}
                                style={{ color: color_codes[item.stance] }}>
                                {item.content} </li>)
                        }
                    </ol>
                    : <div><label>Couldn't find relevant responses</label></div>
                }
                <label>Con</label>
                {con_responses.length > 0 ?
                    <ol>
                        {
                            con_responses.map(item => <li key={item.relevance}
                                style={{ color: color_codes[item.stance] }}>
                                {item.content} </li>)
                        }
                    </ol>
                    : <div><label>Couldn't find relevant responses</label></div>
                }
                <label>Neutral</label>
                {neutral_responses.length > 0 ?
                    <ol>
                        {
                            neutral_responses.map(item => <li key={item.relevance}
                                style={{ color: color_codes[item.stance] }}>
                                {item.content} </li>)
                        }
                    </ol>
                    : <div><label>Couldn't find relevant responses</label></div>
                }
            </div>
        );
    }
    else {
        return (<ol>
            {
                data.wozCandidateResponses.map(item => <li key={item.relevance}
                    style={{ color: color_codes[item.stance] }}>
                    {item.content} </li>)
            }
        </ol>);
    }
}
const CandidateResponse = ({ model, num_responses, classify, utt, dataset, data_type, response }) => {
    const { data } = useSubscription(GET_MESSAGES);
    if (!data) {
        return <div />;
    }
    if (!data.messages || data.messages.length == 0) {
        return <div />;
    }

    //check the sender of the last message
    const lastMessage = data.messages[data.messages.length - 1]
    if (lastMessage.user == 'WOZ') {
        return <div />;
    }

    return (
        <Container>
            <h4>Suggested Responses</h4>
            <CandidateResponseContainer usermessage={lastMessage.content} model={model} num_responses={num_responses}
                classify={classify} utt={utt} dataset={dataset} data_type={data_type} response={response} />
        </Container>
    )
}

const Woz = () => {
    var prev_num_responses = 5;
    const { data } = useSubscription(GET_TOPIC);

    const [state, setState] = useState({
        model: "tfidf",
        checked: false,
        num_responses: 5,
        classify: true,
        utt: "proposition",
        data_type: "moralmaze",
        dataset: "money",
        response: "arg",
        errors: {}
    });

    state.dataset = data ? data.currentTopic.id : "money";

    const [selectTopic] = useMutation(SELECT_TOPIC);

    const selectData = (evt) => {
        const dataset = evt.target.value === "moralmaze" ? "money" : "drugs";
        setState(
            {
                ...state,
                data_type: evt.target.value,
                dataset: dataset
            }
        );
        selectTopic({
            variables: { "id": dataset },
        });

    };

    const selectDataset = (evt) => {
        selectTopic({
            variables: { "id": evt.target.value },
        });
        setState(
            {
                ...state,
                dataset: evt.target.value
            }
        );
    };

    const selectModel = (evt) => {
        setState(
            {
                ...state,
                model: evt.target.value
            }
        );
    };
    const classify = (evt) => {
        setState(
            {
                ...state,
                classify: !state.classify
            }
        );
    };
    const selectUtterance = (value) => {
        setState(
            {
                ...state,
                utt: value
            }
        );
    };
    const selectResponse = (value) => {
        setState(
            {
                ...state,
                response: value
            }
        );
    };
    const verifyNumber = (evt) => {
        const re = /^[0-9\b]+$/;
        if ("" === evt.target.value || re.test(evt.target.value)) {
            let errors = {};
            if (parseInt(evt.target.value) == 0) {
                errors["number"] = "Value cannot be 0";
                setState(
                    {
                        ...state,
                        errors: errors
                    }
                );
            }
            else {
                errors["number"] = "";
                setState(
                    {
                        ...state,
                        num_responses: evt.target.value,
                        errors: errors
                    }
                );
            }
        }
        else {
            let errors = {};
            errors["number"] = "Value has to be a number";
            setState(
                {
                    ...state,
                    errors: errors
                }
            );
        }

    };
    const verifyEmpty = (evt) => {
        if ("" === evt.target.value) {
            let errors = {};
            errors["number"] = ""//"Field Cannot be Empty";
            setState(
                {
                    ...state,
                    num_responses: 5,
                    errors: errors
                }
            );
        }
    };
    const getSuggestions = (evt) => {
        setState(
            {
                ...state,
                checked: !state.checked
            }
        );
    };
    // if(!token) {
    //     return <Login setToken={setToken} />
    //   }
    return (
        <Container fluid max-width='100%'>
            <BrowserRouter>
                <Switch>
                    <Route exact path='/'>
                        <Container fluid>
                            <Row >
                                {/* <Col style={{ display: "flex", width: '30%', border: '1px solid black',borderRadius: '5px'}}> */}
                                <Col xs={5}>
                                    <h4 style={{ marginTop: "10px" }}>Parameters:</h4>
                                    {/* <Row> */}
                                    <Row className="wozClass">
                                        <Col xs={1} style={{ marginTop: "auto", marginBottom: "auto" }}>
                                            <label >Data:</label>
                                        </Col>
                                        <Col xs={2} style={{ marginTop: "auto", marginBottom: "auto", marginLeft: "-10px" }}>
                                            <FormSelect id="topicselection" value={state.data_type} onChange={val => selectData(val)}>
                                                <option className="moralmaze" value="moralmaze">Moral Maze</option>
                                                <option className="kialo" value="kialo">Kialo</option>
                                            </FormSelect>
                                        </Col>
                                        <Col xs={2} style={{ marginTop: "auto", marginBottom: "auto", marginLeft: "-5px" }}>
                                            <label >Dataset:</label>
                                        </Col>
                                        <Col xs={3} style={{ marginTop: "auto", marginBottom: "auto", marginLeft: "-40px" }}>
                                            <FormSelect id="topicselection" value={state.dataset} onChange={val => selectDataset(val)}>
                                                {state.data_type === "moralmaze" ?
                                                    (
                                                        <>
                                                            <option className="money" value="money">MoneyMorality</option>
                                                            <option className="empire" value="empire" >BritishEmpire</option>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <option className="drugs" value="drugs">Drugs</option>
                                                        </>
                                                    )
                                                }
                                            </FormSelect>
                                            {/* <Dataset data_type={state.data_type} dataset={state.dataset} /> */}
                                        </Col>
                                        <Col xs={2} style={{ marginTop: "auto", marginBottom: "auto", marginLeft: "-10px" }}>
                                            <label >Model:</label>
                                        </Col>
                                        <Col xs={3} style={{ marginLeft: "-50px" }}>
                                            <FormSelect value={state.model} onChange={val => selectModel(val)}>
                                                <option value="tfidf">TF-IDF</option>
                                                <option value="word2vec" >Word2Vec</option>
                                                <option value="glove">GloVe</option>
                                                <option value="sbert">SBERT</option>
                                            </FormSelect>
                                        </Col>
                                        <Col xs={3} style={{ marginTop: "15px", marginBottom: "auto" }}>
                                            <label >#Responses:</label>
                                        </Col>
                                        <Col xs={2} style={{ marginTop: "15px", marginBottom: "auto", marginLeft: "-65px" }}>
                                            <input value={state.num_responses} size="2" style={{ height: "30" }} onChange={val => verifyNumber(val)} onBlur={val => verifyEmpty(val)} />
                                            <span style={{ color: "red" }}>{state.errors["number"]}</span>
                                        </Col>
                                        <Col xs={6} style={{ marginTop: "15px", marginBottom: "auto", marginLeft: "-40px" }}>
                                            <FormCheckbox checked={state.classify} onChange={val => classify(val)}>
                                                Classify Responses
                                                </FormCheckbox>
                                        </Col>
                                        <Col xs={5} style={{ marginTop: "5px", marginBottom: "auto" }}>
                                            <label >Response Type:</label>
                                        </Col>
                                        <Col xs={13} style={{ marginTop: "10px", marginBottom: "auto", marginLeft: "-130px" }}>
                                            <FormRadio
                                                name="utt"
                                                checked={state.utt === "locution"}
                                                onChange={val => selectUtterance("locution")}
                                            >
                                                Locution
                                                </FormRadio>
                                            <FormRadio
                                                name="utt"
                                                checked={state.utt === "proposition"}
                                                onChange={val => selectUtterance("proposition")}
                                            >
                                                Proposition
                                                </FormRadio>
                                        </Col>
                                        <Col xs={2} style={{ marginTop: "5px", marginBottom: "auto", marginLeft: "10px" }}>
                                            <label >Retrieve:</label>
                                        </Col>
                                        <Col xs={5} style={{ marginTop: "5px", marginBottom: "auto", marginLeft: "-30px" }}>
                                            <FormRadio
                                                name="response"
                                                checked={state.response === "arg"}
                                                onChange={val => selectResponse("arg")}
                                            >
                                                Most similar argument
                                                </FormRadio>
                                            <FormRadio
                                                name="response"
                                                checked={state.response === "arg_response"}
                                                onChange={val => selectResponse("arg_response")}
                                            >
                                                Response to most similar argument
                                                </FormRadio>
                                        </Col>
                                    </Row>
                                    <Row>
                                        <Col>
                                            <label>Get Suggestions</label>
                                            <FormCheckbox
                                                toggle
                                                checked={state.checked}
                                                onChange={val => getSuggestions(val)}>
                                            </FormCheckbox>
                                        </Col>
                                    </Row>
                                    <Row>
                                        {state.checked ? <CandidateResponse model={state.model} num_responses={state.num_responses}
                                            classify={state.classify} utt={state.utt} dataset={state.dataset} data_type={state.data_type} response={state.response} /> : <div />}
                                    </Row>
                                    {/* </Row> */}
                                </Col>
                                <Col xs={7}>
                                    <Chat />
                                </Col>
                            </Row>
                        </Container>
                    </Route>
                    {/* <Route path='/user:id'>
                    <Child />
                </Route> */}
                </Switch>
            </BrowserRouter>
        </Container>
    )
}


// const Child = () => {
//     // We can use the `useParams` hook here to access
//     // the dynamic pieces of the URL.
//     // const {id} = useParams();
//     // if  (id === ':1111') {
//     //     return <Chat />;
//     // }
//     // else {
//     //     return <h2>The link you provided is invalid.</h2>
//     // }

//   }


export default () => (
    <ApolloProvider client={client}>
        <Woz />
    </ApolloProvider>
);