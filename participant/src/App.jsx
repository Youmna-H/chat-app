import React from "react";
import ReactDOM from "react-dom";

import "./index.css";
import "bootstrap/dist/css/bootstrap.min.css";
import "shards-ui/dist/css/shards.min.css";
import { BrowserRouter, Route, Switch } from 'react-router-dom'
import { Container, Row, Col } from "shards-react";
import Chat from 'chat/Chat'; //chat is the remote name of the client

const App = () => (
    <Container>
        <BrowserRouter>
            <Switch>
                <Route path='/'>
                    <Chat />
                </Route>
            </Switch>
        </BrowserRouter>
    </Container>
    );

ReactDOM.render(<App />, document.getElementById("app"));
