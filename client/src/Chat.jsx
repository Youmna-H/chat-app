import React from 'react';
import {
  ApolloClient,
  InMemoryCache,
  ApolloProvider,
  ApolloProviderHooks,
  useSubscription,
  useMutation,
  gql,
} from "@apollo/client";
import { WebSocketLink } from "@apollo/client/link/ws";
import { Container, Row, Col, FormInput, Button, Text } from "shards-react";
import Login from './Login';
import Header from './Header';
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

//subscription instead of query
const GET_MESSAGES = gql`
  subscription {
    messages {
      id
      user
      content
    }
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

const POST_MESSAGE = gql`
  mutation($user: String!, $content: String!) {
    postMessage(user: $user, content: $content)
  }
`;


const Messages = ({ user }) => {
  // const { data } = useQuery(GET_MESSAGES, {
  //     pollInterval: 500,
  // }}; 
  //we don't need to pull with subscriptions!
  const { data } = useSubscription(GET_MESSAGES);
  const uiContent_ref = React.useRef(null);
  React.useEffect(() => {
    if (!data) return;
    //console.log('render scrol',uiContent_ref.current.scrollHeight,)
    uiContent_ref.current?.scrollTo(0, uiContent_ref.current.scrollHeight)
  }, [data])
  if (!data) {
    return null;
  }
  return (
    <>
      <Container fluid max-width='100%'>
        <div
          ref={uiContent_ref}
          style={{
            height: '500px',
            overflowY: 'auto',
            padding: '10px'

          }}>
          {/* user is renamed messageUser to avoid confusion with the user in Messages */}
          {data.messages.map(({ id, user: messageUser, content }) => (
            <div key={id}
              style={{
                display: "flex",
                justifyContent: user === messageUser ? "flex-end" : "flex-start",
                paddingBottom: "1em",
              }}
            >
              {user !== messageUser && (
                <div
                  style={{
                    height: 50,
                    width: 60,
                    marginRight: "0.5em",
                    border: "2px solid #e5e6ea",
                    borderRadius: 25,
                    textAlign: "center",
                    fontSize: "18pt",
                    paddingTop: 5,
                  }}
                >
                  {messageUser}
                  {/* {messageUser}.slice(0, 2).toUpperCase()} */}
                </div>
              )}
              <div
                style={{
                  background: user === messageUser ? "#17c671" : "#e5e6ea",
                  color: user === messageUser ? "white" : "black",
                  padding: "1em",
                  borderRadius: "1em",
                  maxWidth: "60%",
                }}
              >
                {content}
              </div>
            </div>
          ))
          }
        </div>
      </Container>
    </>
  );
}

const Topic = () => {
  // const { data } = useQuery(GET_MESSAGES, {
  //     pollInterval: 500,
  // }}; 
  //we don't need to pull with subscriptions!

  const { data } = useSubscription(GET_TOPIC);

  if (!data) {
    return (
      <div>
        <h4 className="topic" style={{ marginTop: "10px" }}>Topic: Morality of Money</h4>
        <p style={{ border: "1px solid black", borderRadius: "25px", padding: "10px" }}>
          But the crisis has reinforced the more old fashioned view,
          that taking on unaffordable debts, nationally or individually,
          is inherently wrong, and bankruptcy a matter of shame.  Either way,
          how do you strike a moral balance between the interests of the lender and the borrower?
          The morality of money and debt is our moral maze tonight
          </p>
      </div>
    );
  }
  else {
    return (
      <div>
        <h4 className="topic" style={{ marginTop: "10px" }}>Topic: {data.currentTopic.topic}</h4>
        <p style={{ border: "1px solid black", borderRadius: "25px", padding: "10px" }}>
          {data.currentTopic.text}
        </p>
      </div>
    );
  }
}

const Chat = () => {
  const appuser = document.getElementById("app").getAttribute('value');
  const [state, stateSet] = React.useState({
    user: appuser,
    content: "",
  });

  const [postMessage] = useMutation(POST_MESSAGE);

  const onSend = () => {
    if (state.content.length > 0) {
      postMessage({
        variables: state,
      });
    }
    stateSet({
      ...state,
      content: "",
    });
  };

  return (
    <Container>
      {/* <Row> */}
      <Row>
        <Container fluid max-width='100%' >
          <Topic />
          {/* <h4 className="topic" style={{marginTop:"10px"}}>Topic:</h4>
            <p style={{border: "1px solid black", borderRadius: "25px", padding: "10px"}}>
              But the crisis has reinforced the more old fashioned view, 
              that taking on unaffordable debts, nationally or individually, 
              is inherently wrong, and bankruptcy a matter of shame.  Either way, 
              how do you strike a moral balance between the interests of the lender and the borrower?
               The morality of money and debt is our moral maze tonight
          </p> */}
        </Container>
      </Row>
      <Row>
        <Container>
          {/* <Header/>
            <Route exact path="/login" component={Login} /> */}
          <div><Messages user={state.user} /></div>
          <Row>
            <Col xs={2} style={{ padding: 0 }}>
              {/* <label>  {state.user}</label> */}
              {/* <FormInput 
                        label = "User"
                        value  = {state.user}
                        onChange = {(evt) => stateSet(
                            {
                                ...state,
                                user: evt.target.value,
                            }
                        )}
                    /> */}
            </Col>
            <Col xs={8}>
              <FormInput
                label="Content"
                value={state.content}
                onChange={(evt) => stateSet(
                  {
                    ...state,
                    content: evt.target.value,
                  }
                )}
                onKeyUp={(evt) => {
                  if (evt.keyCode === 13) {
                    onSend();
                  }
                }}
              />

            </Col>
            <Col xs={2} style={{ padding: 0 }}>
              <Button onClick={() => onSend()} style={{ width: '100%' }}>
                Send
                  </Button>
            </Col>
          </Row>
        </Container>
      </Row>
      {/* </Row> */}
    </Container>
  )
}

export default () => (
  <ApolloProvider client={client}>
    <Chat />
  </ApolloProvider>
);