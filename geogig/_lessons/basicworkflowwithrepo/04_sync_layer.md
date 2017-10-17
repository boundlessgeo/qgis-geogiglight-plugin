Assuming that you are happy with the changes you made, you can now
transfer them to the GeoGig repository.

* In the **Layers panel**, right-click the *Buildings* layer. From the
  context menu, select **GeoGig > Sync layer with branch...**. The
  **Syncronize layer to repository branch** dialog opens.

* In the **Syncronize layer to repository branch**, set the **Branch**
  to `john_edits` and add a **Message to describe the update**. For example,
  `"Updates building in Block 1025"`. Click **OK**

    ![commit_message](commit_message.png)

You can confirm that the changes were saved in the GeoGig repository.

* In the **Repository history**, expand both *master*
  and *john_edits* branches. You will see that the branches history
  will differ on one commit. The one you have just done.

    ![branches_difference](branches_difference.png)

Once you are done, click **Next step**.