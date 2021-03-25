const { GraphQLServer, PubSub } = require("graphql-yoga");
const { spawn,spawnSync,execSync } = require('child_process');
//import DateTimeResolver from 'graphql-scalars';

const dialogues = [];
const messages = [];
const users = [];

const topics =  {"money": {"topic":"Morality of Money", "text": "But the crisis has reinforced the more old fashioned view, that taking on unaffordable debts, nationally or individually, is inherently wrong, and bankruptcy a matter of shame.  Either way, how do you strike a moral balance between the interests of the lender and the borrower? The morality of money and debt is our moral maze tonight"},
"empire":{"topic":"British Empire","text":"Is it right to make moral judgments about the past through the prism of our modern sensibilities? Should we be held responsible for the sins of Empire and if so where should it stop? That's our Moral Maze tonight."},
"drugs":{"topic":"","text":"All drugs should be legalised."}};

var currentTopic = {"id":"money","topic":"Morality of Money", "text": "But the crisis has reinforced the more old fashioned view, that taking on unaffordable debts, nationally or individually, is inherently wrong, and bankruptcy a matter of shame.  Either way, how do you strike a moral balance between the interests of the lender and the borrower? The morality of money and debt is our moral maze tonight"};
//topic and topictext
//graphql needs typedefs
//! means the field is required
//we get the messages via the Query type
//messages: [Message!] return an array of messages
//TODO sender is user in Message
//TODO modify type of time stamp

// type Dialogue {
//     id: ID!
//     participants: [!User]
//     messages: [Message!]
// }
// createDialogue(participants: [User!]): ID!
// type User {
//   id: ID!
//   name: String!
//   role: String!
//  }
const typeDefs = `

  type Message {
    id: ID!
    user: String!
    content: String!
  }

  type WozResponse {
    relevance: Int!
    content: String!
    stance: String
  }

  type Topic {
    id: String!
    topic: String!
    text: String!
  }

  type Query {
    messages: [Message!]
    wozCandidateResponses(usermessage:String!, 
      model: String,
      num_responses: Int,
      classify: Int,
      utt: String,
      dataset: String,
      data_type: String
      ): [WozResponse!]
  }

  type Mutation {
    postMessage(user: String!, content: String!): ID!
    selectTopic(id: String!): String!
  }

  type Subscription {
    messages: [Message!]
    currentTopic: Topic!

  }
`;
//    currentTopic: Topic!
const subscribers = [];
const onMessagesUpdates = (fn) => subscribers.push(fn); //to add a new subscriber to subscribers
const onTopicUpdates = (fn) => subscribers.push(fn);
var wozCanndidateResponses = [];

//how do we get the data
//resolvers match the keys in the typedefs
//mutations is like post in the rest world

const resolvers = {
  // DateTime: DateTimeResolver,
  Query: {
    messages: () => messages,
    wozCandidateResponses: (parent, {usermessage, model, num_responses, classify, utt, dataset, data_type}) => {
      if (num_responses <= 0)
      {
        return [];
      }
      wozCanndidateResponses = [];
      const python = data_type === "moralmaze" ?
      spawnSync('python3', ['python/read_json.py', '-q', usermessage, '-m', model, '-n', 
      num_responses, "--responses_per_stance", classify, "-u", utt === 'locution' ? "l" : "i", "-d", dataset])
      : 
      spawnSync('python3', ['python/kialo.py', '-q', usermessage, '-m', model, '-n', 
      num_responses, "--responses_per_stance", classify, "-d", dataset]);
    //   const python = execSync('python3 python/kialo.py -q "hi"', function(error, stdout, stderr) {
    //     console.log(stdout);
    //     console.log(error);
    //     console.log(stderr);
    // });
      // collect data from script
      var dataToSend = python.stdout.toString();
      var stances =  [];
      var responses = [];
      //this is how the responses are splitted in python "###///"
      //delimeter between responses and stances is "$!$!$"
      if (classify === 1 && data_type === 'moralmaze')
      {
        var responses_all = dataToSend.trim().split("$!$!$");
        var responses_pro = responses_all[0].split("###///");
        var responses_con = responses_all[1].split("###///");
        var responses_neutral = responses_all[2].split("###///");
        for (var i = 0; i < responses_pro.length; i++) {
          stances.push("pro");
        }
        for (var i = 0; i < responses_con.length; i++) {
          stances.push("con");
        }
        for (var i = 0; i < responses_neutral.length; i++) {
          stances.push("neutral");
        }
        responses = responses_pro.concat(responses_con, responses_neutral)
      }
      else
      {
        var responses_stances = dataToSend.trim().split("$!$!$"); //this is how the responses are splitted in python
        responses = responses_stances[0].split("###///");
        stances = responses_stances[1].split("###///");
      }

      // python.stdout.on('close', function() {
      responses.forEach(myFunction)
      function myFunction(item, index, arr) {
        let stance = stances[index]
        wozCanndidateResponses.push({relevance:index, content:item, stance:stance});
      }
      return wozCanndidateResponses;
    }
    // users:  () => users
  },

  Mutation: {
    //   createDialogue: (parent, {participants}) => {
    //     const id = Math.random().toString(36).slice(2, 15); //TODO generate unique id
    //     dialogues.push( {
    //         id,
    //         participants,
    //         messages
    //     });
    //     subscribers.forEach((fn) => fn());
    //     return id;
    //   },
    // createUser: (parent, {name, role}) => {
    //     id = Math.random().toString(36).slice(2, 15);//users.length;
    //     while ( users.includes(id) ) {
    //       id = Math.random().toString(36).slice(2, 15);
    //     }
    //     users.push({
    //         id,
    //         name,
    //         role
    //     });
    //     return id;
    // },
    selectTopic: (parent, { id }) => {
      var t = topics[id];
      currentTopic = {"id":id, "topic":t.topic, "text":t.text};
      subscribers.forEach((fn) => fn());
      return currentTopic.id;
    },
    postMessage: (parent, { user, content }) => {
      const id = messages.length;
      messages.push({
        id,
        user,
        content
      });
      subscribers.forEach((fn) => fn());
      return id;
    },
  },
  Subscription: {
    messages: {
      subscribe: (parent, args, { pubsub }) => {
        const channel = Math.random().toString(36).slice(2, 15);
        onMessagesUpdates(() => pubsub.publish(channel, { messages }));
        setTimeout(() => pubsub.publish(channel, { messages }), 0);
        return pubsub.asyncIterator(channel);
      }},
      currentTopic: {
        subscribe: (parent, args, { pubsub }) => {
          const channel = Math.random().toString(36).slice(2, 15);
          onTopicUpdates(() => pubsub.publish(channel, { currentTopic }));
          setTimeout(() => pubsub.publish(channel, { currentTopic }), 0);
          return pubsub.asyncIterator(channel);
        },
    }
  }
};

const pubsub = new PubSub();
const server = new GraphQLServer({ typeDefs, resolvers, context: { pubsub } });
server.start(({ port }) => {
  console.log(`Server on http://localhost:${port}/`);
});