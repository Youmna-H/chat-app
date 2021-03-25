import React, { useState } from 'react';
import ReactDOM from "react-dom";
import { useParams } from 'react-router';
import "./index.css";
import "bootstrap/dist/css/bootstrap.min.css";
import "shards-ui/dist/css/shards.min.css";
import { BrowserRouter, Route, Switch } from 'react-router-dom'
import { Container, 
    DropdownToggle,
    DropdownMenu,
    DropdownItem,
    Button,
    Dropdown,
    FormSelect } from "shards-react";
import {
        ApolloClient,
        InMemoryCache,
        ApolloProvider,
        ApolloProviderHooks,
        useSubscription,
        useMutation,
        gql,
      } from "@apollo/client";
import Chat from 'chat/Chat'; //chat is the remote name of the client

import Woz from './Woz';

const App = () => <Woz />;
  

ReactDOM.render(<App />, document.getElementById("app"));

