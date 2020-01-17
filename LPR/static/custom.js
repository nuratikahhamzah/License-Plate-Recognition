
// Initialise Pusher

const pusher = new Pusher('6d3a12086650daf9eda5', {
    cluster: 'ap1',
    encrypted: true
});

var channel = pusher.subscribe('Plate4');

// listen forevents on your channel
channel.bind('new-record', (data) => {

				   $('#plates').append(`
				        <tr id="${data.data.id}">
				            <th scope="row"> ${data.data.masa} </th>		            
				            <td> <img src="data:image/png;base64,${data.data.image}" alt="image"/> </td>
				            <td> ${data.data.txt} </td>

				        </tr>
				  
				   `)
				});

// channel.bind('update-record', (data) => {

//     $(`#${data.data.id}`).html(`
//         <th scope="row"> ${data.data.image} </th>
//         <td> ${data.data.txt} </td>
//         <td> ${data.data.masa} </td>
//     `)

//  });