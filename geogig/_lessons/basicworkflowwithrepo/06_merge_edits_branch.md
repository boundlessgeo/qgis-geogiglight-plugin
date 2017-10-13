Assuming that you are happy with all the changes, you can now transfer
them to the *master* branch.

* If needed, in the **GeoGig Navigator, select the *building2017_update*
  repository so that it shows the its branches in the **Repository
  history** below.

* In the **Repository history**, right-click the *John_edits* branch and
  select **Merge this branch into > master** from the context menu.

* In the **Layers panel**, right-click the *Buildings* layer. From the
  context menu, select **GeoGig > Sync layer with branch...**. The
  **Syncronize layer to repository branch** dialog opens.

A message on the top of the map canvas will inform that the merge was
done successfully.

You can confirm that all the *john_edits* work was in merge into the
*master* branch by inspecting its commits list.

* In the **Repository history** expand both the *master* and the
  *john_edits* branch. Confirm that all the commits that were previously
  only in the *john_edit* branch are now also available in the *master*
  branch.

This step ends the lesson, click **Finish**.