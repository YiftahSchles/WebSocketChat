let ws; //WebSocket object

function tag(user) {
  // Tag a user - put his name with a @ in the beginning of the message input.
  // when sending the message it will be a direct message to the user
  crntContent = document.getElementById('msg_input').value;
  if (crntContent.startsWith ('@')) // change the user tagged
    document.getElementById('msg_input').value = '@' + user.innerText + ' ' + crntContent.split (' ')[1];
  else { // tag the user (no user is already tagged)
    document.getElementById('msg_input').value = '@' + user.innerText + ' ' + crntContent;
  }
  document.getElementById ('chat').scrollTop = document.getElementById ('chat').scrollHeight;
}

function upload_img() { // upload and send an image in the chat
  //from the file input element #imgFile
  files = document.getElementById('imgFile').files;
  if (files.length > 0) {
    ws.send('{"action": "send_img", "type": "' + files [0].name.split ('.').pop() + '"}');
    fr = new FileReader();
    ws.binaryType = 'arraybuffer';
    ws.binaryData = 'blob';
    fr.onload = function(e) {
      ws.send(e.target.result);
    }
    fr.readAsArrayBuffer(files[0]);
  }
}

function try_login() {
  // try to login to the chat with the username in the input
  username = document.getElementById('username').value;
  if (username.length == 0) return;
  ws = new WebSocket('ws://' + window.location.host + ':[[[PORT_PLACEHOLDER]]]/connect');
  ws.onopen = function(e) {
    //websocket connected
    console.log('connected');
    ws.send("{\"action\": \"login\", \"username\": \"" + username + "\"}");
  };
  ws.onmessage = function(e) {
    //message received from the server
    var data = JSON.parse(e.data);
    if (data["action"] == 'login') {
      if (data["result"] == 'success') {
        //login successful
        //hide login screen and display chat screen
        document.getElementById('loginScreen').classList.add('hidden');
        document.getElementById('chatScreen').classList.remove('hidden');
      } else {
        alert('error. try signing in with a different name');
      }
    }
    if (data['action'] == 'new_msg') {
      //Message received in the chat. display it
      //Add it to the chat screen as plain text to prevent HTML injection
      sender = decodeURIComponent(data['sender']);
      content = decodeURIComponent(data['content']);
      if (sender == 'admin') {
        bold_content = document.createElement('b');
        bold_content.innerText = content;
        document.getElementById('chat').append(bold_content);
      } else {
        bold_content = document.createElement('a');
        bold_content.href = "#msg_input";
        bold_content.innerText = sender;
        bold_content.classList.add('sender');
        unbold_content = document.createElement('div');
        unbold_content.style = 'display: inline;';
        unbold_content.innerText = ': ' + content;
        document.getElementById('chat').append(bold_content);
        document.getElementById('chat').append(unbold_content);
      }
      document.getElementById('chat').innerHTML += '<br>';
    } else if (data['action'] == 'send_img') {
      //image received in the chat. display the image
      sender = decodeURIComponent(data['sender']);
      content = decodeURIComponent(data['content']);
      bold_content = document.createElement('a');
      bold_content.href = "#msg_input";
      bold_content.innerText = sender;
      bold_content.classList.add('sender');
      document.getElementById('chat').append(bold_content);
      document.getElementById('chat').innerHTML += ":<br>";
      img_element = document.createElement('img');
      img_element.src = '/image?imgId=' + content;
      img_element.onload = function() {
        //resize the Image
        //max width = 250px, max height = 400px
        imgs = document.getElementById ('chat').getElementsByTagName('img');
        img_element = imgs [imgs.length - 1];
        ratio = (1.0 + img_element.width) / img_element.height
        if (img_element.width > 250) {
          img_element.height = 250.0 / ratio;
          img_element.width = 250;
        }
        if (img_element.height > 400) {
          img_element.width = ratio * 400;
          img_element.height = 400;
        }
      }
      document.getElementById('chat').append(img_element);
      document.getElementById('chat').innerHTML += "<br>";
    }
    document.getElementById ('chat').scrollTop = document.getElementById ('chat').scrollHeight;
  }
}

function send_msg() {
  //send a message in the chat
  msg = document.getElementById('msg_input').value;
  document.getElementById('msg_input').value = "";
  if (msg.length == 0) return;
  msg = encodeURIComponent(msg);
  ws.send('{"action": "send_msg", "content": "' + msg + '"}')
}

window.onload = function() {
  document.getElementById('username').addEventListener('keypress', function(x) {
    if (x.keyCode == 13) try_login();
  });
  document.getElementById('msg_input').addEventListener('keypress', function(x) {
    if (x.keyCode == 13) send_msg();
  });
  document.addEventListener('click', function(e) {
    if (e.target.classList.contains('sender'))
      tag(e.target);
  });
}
